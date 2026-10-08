from uuid import UUID

from supabase import AsyncClient

from domain.entities.preferencias import Preferencias
from domain.repositories.preferencias_repository import PreferenciasRepository

TABLE = "Preferencias"

class SupabasePreferenciasRepository(PreferenciasRepository):
    def __init__(self, client: AsyncClient):
        self._client = client

    async def get_by_user_id(self, user_id: UUID) -> Preferencias | None:
        res = (
            await self._client.table(TABLE)
            .select("id, user_id")
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )
        return self._to_entity(res.data) if res and res.data else None

    async def save(self, preferencias: Preferencias) -> Preferencias:
        payload = {"user_id": str(preferencias.user_id)}
        # si ya tiene id (update), se incluye, si no, la db lo asigna
        if preferencias.id is not None:
            payload["id"] = preferencias.id

        res = (
            await self._client.table(TABLE)
            .upsert(payload, on_conflict="user_id")
            .execute()
        )
        return self._to_entity(res.data[0])

    @staticmethod
    def _to_entity(row: dict) -> Preferencias:
        return Preferencias(id=row["id"], user_id=UUID(row["user_id"]))