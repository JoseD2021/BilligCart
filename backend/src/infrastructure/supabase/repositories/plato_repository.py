from supabase import AsyncClient
from postgrest.exceptions import APIError

from domain.errors import InvalidRequestBodyError
from domain.enums.plato_tipo import PlatoTipo
from domain.entities.plato import Plato
from domain.repositories.plato_repository import PlatoRepository

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
        
        self._validations(plato)
        
        res = (
            await self._client.table(TABLE)
            .insert(payload)
            .execute()
        )
        
        return res.data[0]
            
    async def update(self, plato: Plato) -> Plato:
        self._validations(plato)
        
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
            raise InvalidRequestBodyError(f"Plato with id {plato.id} not found")
        
        return res.data[0]
    
    async def get_by_menu_day(self, menu_id: int, day: int) -> list[Plato]:
        res = (
            await self._client.table(TABLE)
            .select("*")
            .eq("menu_id", menu_id)
            .eq("day", day)
            .execute()
        )
        
        return [Plato(**plato) for plato in res.data]
    
    async def delete_by_id(self, id: int) -> None:
        if not isinstance(id, int) or id <= 0:
            raise InvalidRequestBodyError("id must be a positive integer")
        
        await self._client.table(TABLE).delete().eq("id", id).execute()
    
    def _validations(self, plato: Plato) -> None:
        if plato.day < 1 or plato.day > 7:
            raise InvalidRequestBodyError("Day must be between 1 and 7")
        
        if len(plato.name) == 0:
            raise InvalidRequestBodyError("Name cannot be empty")