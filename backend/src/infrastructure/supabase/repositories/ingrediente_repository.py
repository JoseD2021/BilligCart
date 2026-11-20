from supabase import AsyncClient

from src.domain.entities.ingrediente import Ingrediente, IngredienteFetchInfo
from src.domain.errors import ResourceNotFound
from src.domain.repositories.ingrediente_repository import IngredienteRepository
from src.infrastructure.supabase.repositories.mappers import ingrediente_entity

TABLE = "Ingrediente"

class SupabaseIngredienteRepository(IngredienteRepository):
    def __init__(self, client: AsyncClient):
        self._client = client

    async def create(self, ingr: Ingrediente) -> Ingrediente:
        payload = {
            "name": ingr.name,
            "last_updated": ingr.last_updated.strftime("%Y-%m-%d %H:%M:%S.%f%z"),
            "shop": ingr.shop,
            "price": ingr.price,
            "url": ingr.url
        }
        res = (
            await self._client.table(TABLE)
            .insert(payload)
            .execute()
        )
        return ingrediente_entity(res.data[0])

    async def update(self, ingr: Ingrediente) -> Ingrediente:
        payload = {
            "name": ingr.name,
            "last_updated": ingr.last_updated.strftime("%Y-%m-%d %H:%M:%S.%f%z")
        }

        res = (
            await self._client.table(TABLE)
            .update(payload)
            .eq("id", ingr.id)
            .execute()
        )
        if not res.data:
            raise ResourceNotFound("Ingrediente no encontrado.")
        return ingrediente_entity(res.data[0])

    async def update_fetch_info(self, id: int, fetch_info: IngredienteFetchInfo) -> Ingrediente:
        payload = {
            "last_updated": fetch_info.fetched_at.strftime("%Y-%m-%d %H:%M:%S.%f%z"),
            "shop": fetch_info.shop,
            "price": fetch_info.price,
            "url": fetch_info.url
        }

        res = (
            await self._client.table(TABLE)
            .update(payload)
            .eq("id", id)
            .execute()
        )
        if not res.data:
            raise ResourceNotFound("Ingrediente no encontrado.")
        return ingrediente_entity(res.data[0])

    async def get_all(self) -> list[Ingrediente]:
        res = (
            await self._client.table(TABLE)
            .select("*")
            .execute()
        )

        return [ingrediente_entity(row) for row in res.data] if res and res.data else []

    async def get_by_id(self, id: int) -> Ingrediente | None:
        res = (
            await self._client.table(TABLE)
            .select("*")
            .eq("id", id)
            .execute()
        )

        return ingrediente_entity(res.data[0]) if res and res.data else None

    async def delete_by_id(self, id: int) -> None:
        await self._client.table(TABLE).delete().eq("id", id).execute()
