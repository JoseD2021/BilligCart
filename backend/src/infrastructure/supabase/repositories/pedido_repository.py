from dataclasses import asdict

from supabase import AsyncClient

from src.domain.entities.compra import ShoppingItem
from src.domain.entities.pedido import ESTADOS_PEDIDO, Pedido
from src.domain.repositories.pedido_repository import PedidoRepository
from src.infrastructure.supabase.repositories.mappers import timestamp

SELECT = "*"


class SupabasePedidoRepository(PedidoRepository):
    def __init__(self, client: AsyncClient):
        self.client = client

    async def create(self, pedido: Pedido) -> Pedido:
        payload = asdict(pedido)
        payload.pop("created_at")
        payload.pop("ubicacion", None)
        payload.pop("envio", None)  # se guarda aparte, con set_envio
        await self.client.table("Pedidos").upsert(
            payload, on_conflict="user_id,checkout_key", ignore_duplicates=True,
        ).execute()
        result = await self.client.table("Pedidos").select(SELECT).eq("user_id", pedido.user_id).eq(
            "checkout_key", pedido.checkout_key).execute()
        rows = await self._with_ubicaciones(result.data or [])
        return self._entity(rows[0])

    async def _with_ubicaciones(self, rows: list[dict]) -> list[dict]:
        ids = [str(r["repartidor_id"]) for r in rows if r.get("repartidor_id")]
        if not ids:
            return rows
        try:
            res = await self.client.table("Ubicacion").select("repartidor_id,lat,lng,updated_at,accuracy,heading,speed").in_("repartidor_id", ids).execute()
            by_id = {str(r["repartidor_id"]): r for r in res.data or []}
        except Exception:
            by_id = {}
        for row in rows:
            rid = str(row["repartidor_id"]) if row.get("repartidor_id") else None
            row["ubicacion"] = by_id.get(rid)
        return rows

    async def get_current(self, user_id: str) -> Pedido | None:
        result = await self.client.table("Pedidos").select(SELECT).eq("user_id", user_id).order(
            "created_at", desc=True).limit(1).execute()
        rows = await self._with_ubicaciones(result.data or [])
        return self._entity(rows[0]) if rows else None

    async def get_by_id(self, user_id: str, pedido_id: str) -> Pedido | None:
        result = await self.client.table("Pedidos").select(SELECT).eq("user_id", user_id).eq("id", str(pedido_id)).execute()
        rows = await self._with_ubicaciones(result.data or [])
        return self._entity(rows[0]) if rows else None

    async def list_available(self) -> list[Pedido]:
        result = await self.client.table("Pedidos").select(SELECT).is_("repartidor_id", "null").eq(
            "estado", "pendiente").order("created_at", desc=False).execute()
        rows = await self._with_ubicaciones(result.data or [])
        return [self._entity(row) for row in rows]

    async def list_assigned(self, repartidor_id: str) -> list[Pedido]:
        result = await self.client.table("Pedidos").select(SELECT).eq("repartidor_id", repartidor_id).in_(
            "estado", ["confirmado", "en_camino"]).order("created_at", desc=False).execute()
        rows = await self._with_ubicaciones(result.data or [])
        return [self._entity(row) for row in rows]

    async def get_by_id_for_courier(self, repartidor_id: str, pedido_id: str) -> Pedido | None:
        result = await self.client.table("Pedidos").select(SELECT).eq("repartidor_id", repartidor_id).eq(
            "id", str(pedido_id)).execute()
        rows = await self._with_ubicaciones(result.data or [])
        return self._entity(rows[0]) if rows else None

    async def assign(self, pedido_id: str, repartidor_id: str, repartidor: str | None = None) -> Pedido | None:
        existing = await self.client.table("Pedidos").select(SELECT).eq("id", str(pedido_id)).execute()
        if not existing.data:
            return None
        row = existing.data[0]
        if row.get("repartidor_id") and str(row["repartidor_id"]) != str(repartidor_id):
            return None
        estado_actual = self._entity(row).estado
        if estado_actual not in ("pendiente", "confirmado"):
            rows = await self._with_ubicaciones([row])
            return self._entity(rows[0])
        payload = {"repartidor_id": repartidor_id, "estado": "confirmado"}
        if repartidor:
            payload["repartidor"] = repartidor
        query = self.client.table("Pedidos").update(payload).eq("id", str(pedido_id)).in_("estado", ["pendiente", "confirmado"])
        if not row.get("repartidor_id"):
            query = query.is_("repartidor_id", "null")
        else:
            query = query.eq("repartidor_id", repartidor_id)
        await query.execute()
        result = await self.client.table("Pedidos").select(SELECT).eq("id", str(pedido_id)).execute()
        rows = await self._with_ubicaciones(result.data or [])
        return self._entity(rows[0]) if rows else None

    async def set_envio(self, user_id: str, pedido_id: str, envio: dict) -> Pedido | None:
        await self.client.table("Pedidos").update({"envio": envio}).eq("id", str(pedido_id)).eq(
            "user_id", user_id).execute()
        return await self.get_by_id(user_id, pedido_id)

    async def update_estado(self, pedido_id: str, repartidor_id: str, estado: str) -> Pedido | None:
        await self.client.table("Pedidos").update({"estado": estado}).eq("id", str(pedido_id)).eq(
            "repartidor_id", repartidor_id).execute()
        result = await self.client.table("Pedidos").select(SELECT).eq("id", str(pedido_id)).eq(
            "repartidor_id", repartidor_id).execute()
        rows = await self._with_ubicaciones(result.data or [])
        return self._entity(rows[0]) if rows else None

    @staticmethod
    def _entity(row: dict) -> Pedido:
        raw_estado = row.get("estado")
        estado = raw_estado if raw_estado in ESTADOS_PEDIDO else "pendiente"
        ubicacion = row.get("Ubicacion") or row.get("ubicacion")
        if isinstance(ubicacion, list):
            ubicacion = ubicacion[0] if ubicacion else None
        ubicacion_data = None
        if isinstance(ubicacion, dict) and ubicacion.get("lat") is not None and ubicacion.get("lng") is not None:
            ubicacion_data = {
                "lat": float(ubicacion["lat"]), "lng": float(ubicacion["lng"]),
                "updated_at": ubicacion.get("updated_at"),
                "accuracy": ubicacion.get("accuracy"), "heading": ubicacion.get("heading"),
                "speed": ubicacion.get("speed"),
            }
        menu_id = row.get("menu_id")
        return Pedido(
            id=str(row["id"]), user_id=str(row["user_id"]), menu_id=int(menu_id) if menu_id is not None else 0,
            checkout_key=row.get("checkout_key") or "",
            items=[ShoppingItem(**item) for item in row.get("items", []) or []],
            total=float(row.get("total", 0) or 0), estado=estado,
            repartidor_id=str(row["repartidor_id"]) if row.get("repartidor_id") else None,
            repartidor=row.get("repartidor"),
            created_at=timestamp(row.get("created_at")), ubicacion=ubicacion_data,
            envio=row.get("envio"),
        )
