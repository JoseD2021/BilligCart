from supabase import AsyncClient

from src.domain.entities.plato import Plato
from src.domain.errors import ResourceNotFound
from src.domain.repositories.plato_repository import PlatoRepository
from src.infrastructure.supabase.repositories.mappers import plato_entity

TABLE = "Plato"

class SupabasePlatoRepository(PlatoRepository):
    def __init__(self, client: AsyncClient):
        self._client = client

    async def create(self, plato: Plato) -> Plato:
        payload = {
            "menu_id": plato.menu_id,
            "type": plato.type.value,
            "name": plato.name,
            "day": plato.day,
            "description": plato.description
        }


        res = (
            await self._client.table(TABLE)
            .insert(payload)
            .execute()
        )

        return plato_entity(res.data[0])

    async def update(self, plato: Plato) -> Plato:

        res = (
            await self._client.table(TABLE)
            .update({
                "menu_id": plato.menu_id,
                "type": plato.type.value,
                "name": plato.name,
                "day": plato.day,
                "description": plato.description
            })
            .eq("id", plato.id)
            .execute()
        )

        if len(res.data) == 0:
            raise ResourceNotFound(f"Plato with id {plato.id} not found")

        return plato_entity(res.data[0])

    async def get_by_menu_day(self, menu_id: int, day: int) -> list[Plato]:
        res = (
            await self._client.table(TABLE)
            .select("*")
            .eq("menu_id", menu_id)
            .eq("day", day)
            .execute()
        )

        return [plato_entity(plato) for plato in res.data]

    async def get_by_id(self, id: int) -> Plato | None:
        res = await self._client.table(TABLE).select("*").eq("id", id).execute()
        return plato_entity(res.data[0]) if res and res.data else None

    async def delete_by_id(self, id: int) -> None:
        await self._client.table(TABLE).delete().eq("id", id).execute()
