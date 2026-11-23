from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.domain.enums.role import UserRole
from src.domain.errors import AccessDenied
from src.infrastructure.api.v1.dependencies import (
    get_current_user,
    get_shopping_use_case,
)

router = APIRouter(tags=["Compras y pedidos"])


class EstadoPedidoRequest(BaseModel):
    estado: str


class ConfirmarCompraRequest(BaseModel):
    # El usuario acepta explícitamente dejar fuera los ingredientes sin precio.
    omitir_sin_precio: bool = False


def require_courier(user):
    if getattr(user, "role_enum", UserRole.USER) is not UserRole.REPARTIDOR:
        raise AccessDenied("Solo repartidores pueden realizar esta acción.")
    return user


@router.get("/compras")
async def shopping_list(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    return await use_case.get_list(user.id)


@router.post("/compras/confirmar", status_code=201)
async def confirm(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case),
                  body: ConfirmarCompraRequest | None = None):
    return await use_case.confirm(user.id, body.omitir_sin_precio if body else False)


@router.get("/pedidos/current")
async def current_order(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    return await use_case.current_order(user.id)


@router.get("/pedidos")
async def list_orders(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    return await use_case.list_orders(user.id)


@router.get("/pedidos/{pedido_id}/estado")
async def order(pedido_id: UUID, user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    return await use_case.order(user.id, str(pedido_id))


@router.get("/repartidor/pedidos/disponibles")
async def available_orders(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    require_courier(user)
    return await use_case.available_for_courier()


@router.get("/repartidor/pedidos/asignados")
async def assigned_orders(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    require_courier(user)
    return await use_case.assigned_to_courier(user.id)


@router.post("/repartidor/pedidos/{pedido_id}/aceptar")
async def accept_order(pedido_id: UUID, user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    require_courier(user)
    name = user.email.split("@")[0] if user.email else None
    return await use_case.accept(user.id, str(pedido_id), name)


@router.patch("/repartidor/pedidos/{pedido_id}/estado")
async def update_order_status(pedido_id: UUID, body: EstadoPedidoRequest, user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    require_courier(user)
    return await use_case.update_status(user.id, str(pedido_id), body.estado)
