from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # solo para tipado
    from supabase import AsyncClient

# Tabla pedidos(id, user_id, repartidor_id)
TABLE = "Pedidos"


class SupabaseOrderAccess:
    """Implementa OrderAccessPolicy con el cliente de Supabase compartido del proyecto."""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def _pedido(self, order_id: str) -> dict | None:
        res = await (
            self._client.table(TABLE)
            .select("user_id,repartidor_id")
            .eq("id", order_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res and res.data else None

    async def is_customer(self, user_id: str, order_id: str) -> bool:
        pedido = await self._pedido(order_id)
        return pedido is not None and str(pedido.get("user_id")) == str(user_id)

    async def is_courier(self, user_id: str, order_id: str) -> bool:
        pedido = await self._pedido(order_id)
        return pedido is not None and str(pedido.get("repartidor_id")) == str(user_id)
