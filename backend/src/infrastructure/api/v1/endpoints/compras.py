import logging
from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.enums.role import UserRole
from src.domain.errors import AccessDenied
from src.infrastructure.api.v1.dependencies import (
    get_current_user,
    get_shopping_use_case,
    get_supabase_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Compras y pedidos"])


class EstadoPedidoRequest(BaseModel):
    estado: str


class ConfirmarCompraRequest(BaseModel):
    # El usuario acepta explícitamente dejar fuera los ingredientes sin precio.
    omitir_sin_precio: bool = False
    # Ids (ShoppingItem.id) de los productos que el usuario marcó para comprar.
    # Si no se envía, se incluye toda la lista.
    items_ids: list[str] | None = None


class EnvioRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    direccion: str = Field(min_length=1, max_length=300)
    referencia: str | None = Field(default=None, max_length=300)
    # El mapa/GPS completa lat y lng; siempre vienen los dos o ninguno.
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def coordenadas_completas(self):
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat y lng deben enviarse juntos")
        return self


def require_courier(user):
    if getattr(user, "role_enum", UserRole.USER) is not UserRole.REPARTIDOR:
        raise AccessDenied("Solo repartidores pueden realizar esta acción.")
    return user


async def pedidos_con_estado_pago(pedidos, client):
    """Añade `pagado` a los pedidos del repartidor desde los Pagos confirmados.

    `None` significa que no se pudo consultar el estado; el cliente no debe
    mostrar la nota de pago pendiente en ese caso.
    """
    if not pedidos:
        return []
    ids = [str(p.id) for p in pedidos]
    try:
        result = await client.table("Pagos").select("order_id,status").in_(
            "order_id", ids).eq("status", "succeeded").execute()
        pagados = {str(row["order_id"]) for row in (result.data or [])
                   if row.get("status") == "succeeded"}
    except Exception:
        logger.warning("No se pudo consultar el estado de pago de los pedidos del repartidor", exc_info=True)
        return [asdict(p) | {"pagado": None} for p in pedidos]
    return [asdict(p) | {"pagado": str(p.id) in pagados} for p in pedidos]


@router.get("/compras")
async def shopping_list(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    return await use_case.get_list(user.id)


@router.post("/compras/confirmar", status_code=201)
async def confirm(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case),
                  body: ConfirmarCompraRequest | None = None):
    omitir = body.omitir_sin_precio if body else False
    if body and body.items_ids is not None:
        return await use_case.confirm(user.id, omitir, items_ids=body.items_ids)
    return await use_case.confirm(user.id, omitir)


@router.get("/pedidos/current")
async def current_order(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    return await use_case.current_order(user.id)

@router.get("/pedidos")
async def list_orders(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    return await use_case.list_orders(user.id)

@router.put("/pedidos/{pedido_id}/envio")
async def set_delivery(pedido_id: UUID, body: EnvioRequest, user=Depends(get_current_user),
                       use_case=Depends(get_shopping_use_case)):
    return await use_case.set_delivery(user.id, str(pedido_id), body.model_dump())

@router.get("/pedidos/{pedido_id}/estado")
async def order(pedido_id: UUID, user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    return await use_case.order(user.id, str(pedido_id))


@router.get("/repartidor/pedidos/disponibles")
async def available_orders(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case),
                           client=Depends(get_supabase_client)):
    require_courier(user)
    pedidos = await use_case.available_for_courier()
    return await pedidos_con_estado_pago(pedidos, client)


@router.get("/repartidor/pedidos/asignados")
async def assigned_orders(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case),
                          client=Depends(get_supabase_client)):
    require_courier(user)
    pedidos = await use_case.assigned_to_courier(user.id)
    return await pedidos_con_estado_pago(pedidos, client)


@router.post("/repartidor/pedidos/{pedido_id}/aceptar")
async def accept_order(pedido_id: UUID, user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    require_courier(user)
    name = user.email.split("@")[0] if user.email else None
    return await use_case.accept(user.id, str(pedido_id), name)


@router.patch("/repartidor/pedidos/{pedido_id}/estado")
async def update_order_status(pedido_id: UUID, body: EstadoPedidoRequest, user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    require_courier(user)
    return await use_case.update_status(user.id, str(pedido_id), body.estado)
