from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase import AsyncClient

TABLE = "Pedidos"


class SupabaseOrderAccess:
    """Controla acceso a tracking. Permite repartidor asignado o tomar pedido pendiente."""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def _pedido(self, order_id: str) -> dict | None:
        res = await (
            self._client.table(TABLE)
            .select("user_id,repartidor_id,estado")
            .eq("id", str(order_id))
            .limit(1)
            .execute()
        )
        return res.data[0] if res and res.data else None

    async def is_customer(self, user_id: str, order_id: str) -> bool:
        pedido = await self._pedido(order_id)
        return pedido is not None and str(pedido.get("user_id")) == str(user_id)

    async def is_courier(self, user_id: str, order_id: str) -> bool:
        pedido = await self._pedido(order_id)
        if pedido is None:
            return False
        repartidor = pedido.get("repartidor_id")
        if repartidor and str(repartidor) == str(user_id):
            return True
        if not repartidor and pedido.get("estado") in ("pendiente", "confirmado"):
            await self._client.table(TABLE).update(
                {"repartidor_id": user_id, "estado": "confirmado"}
            ).eq("id", str(order_id)).is_("repartidor_id", "null").in_("estado", ["pendiente", "confirmado"]).execute()
            current = await self._pedido(order_id)
            return current is not None and str(current.get("repartidor_id")) == str(user_id)
        return False
