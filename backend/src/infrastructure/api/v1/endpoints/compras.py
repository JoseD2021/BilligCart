from uuid import UUID

from fastapi import APIRouter, Depends

from src.infrastructure.api.v1.dependencies import (
    get_current_user,
    get_shopping_use_case,
)

router = APIRouter(tags=["Compras y pedidos"])


@router.get("/compras")
async def shopping_list(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    return await use_case.get_list(user.id)


@router.post("/compras/confirmar", status_code=201)
async def confirm(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    return await use_case.confirm(user.id)


@router.get("/pedidos/current")
async def current_order(user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    return await use_case.current_order(user.id)


@router.get("/pedidos/{pedido_id}/estado")
async def order(pedido_id: UUID, user=Depends(get_current_user), use_case=Depends(get_shopping_use_case)):
    return await use_case.order(user.id, str(pedido_id))
