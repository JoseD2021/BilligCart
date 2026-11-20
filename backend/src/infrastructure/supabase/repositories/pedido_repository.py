from dataclasses import asdict

from supabase import AsyncClient

from src.domain.entities.compra import ShoppingItem
from src.domain.entities.pedido import Pedido
from src.domain.repositories.pedido_repository import PedidoRepository
from src.infrastructure.supabase.repositories.mappers import timestamp


class SupabasePedidoRepository(PedidoRepository):
    def __init__(self, client: AsyncClient):
        self.client = client

    async def create(self, pedido: Pedido) -> Pedido:
        payload = asdict(pedido)
        payload.pop("created_at")
        await self.client.table("Pedidos").upsert(
            payload, on_conflict="user_id,checkout_key", ignore_duplicates=True,
        ).execute()
        result = await self.client.table("Pedidos").select("*").eq("user_id", pedido.user_id).eq(
            "checkout_key", pedido.checkout_key).execute()
        return self._entity(result.data[0])

    async def get_current(self, user_id: str) -> Pedido | None:
        result = await self.client.table("Pedidos").select("*").eq("user_id", user_id).order(
            "created_at", desc=True).limit(1).execute()
        return self._entity(result.data[0]) if result.data else None

    async def get_by_id(self, user_id: str, pedido_id: str) -> Pedido | None:
        result = await self.client.table("Pedidos").select("*").eq("user_id", user_id).eq("id", pedido_id).execute()
        return self._entity(result.data[0]) if result.data else None

    @staticmethod
    def _entity(row: dict) -> Pedido:
        return Pedido(
            id=str(row["id"]), user_id=str(row["user_id"]), menu_id=row["menu_id"],
            checkout_key=row["checkout_key"], items=[ShoppingItem(**item) for item in row["items"]],
            total=float(row["total"]), etapa=row["etapa"],
            repartidor_id=str(row["repartidor_id"]) if row.get("repartidor_id") else None,
            repartidor=row.get("repartidor"), tiempo_estimado=row.get("tiempo_estimado"),
            created_at=timestamp(row.get("created_at")),
        )
