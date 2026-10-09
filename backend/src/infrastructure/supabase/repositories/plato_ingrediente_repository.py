from supabase import AsyncClient

from domain.repositories.plato_ingrediente_repository import PlatoIngredienteRepository
from domain.entities.plato_ingrediente import PlatoIngrediente

TABLE = "PlatoIngrediente"

class SupabasePlatoIngredienteRepository(PlatoIngredienteRepository):
    def __init__(self, client: AsyncClient):
        self._client = client

    async def create(self, pltingr: PlatoIngrediente) -> PlatoIngrediente:
        payload = {
            "quantity": pltingr.quantity,
            "unit": pltingr.unit,
            "plato_id": pltingr.plato_id,
            "ingrediente_id": pltingr.ingrediente_id
        }
        res = (
            await self._client.table(TABLE)
            .insert(payload)
            .execute()
        )
        return res.data[0]
    
    async def create_many(self, pltingr_list: list[PlatoIngrediente]) -> list[PlatoIngrediente]:
        payload = [
            {
                "quantity": pltingr.quantity,
                "unit": pltingr.unit,
                "plato_id": pltingr.plato_id,
                "ingrediente_id": pltingr.ingrediente_id
            }
            for pltingr in pltingr_list
        ]
        res = (
            await self._client.table(TABLE)
            .insert(payload)
            .execute()
        )
        return res.data
    
    async def update(self, pltingr: PlatoIngrediente) -> PlatoIngrediente:
        payload = {
            "quantity": pltingr.quantity,
            "unit": pltingr.unit
        }
        
        res = (
            await self._client.table(TABLE)
            .update(payload)
            .eq("id", pltingr.id)
            .execute()
        )
        return res.data[0]
    
    async def delete_by_id(self, id: int) -> None:
        await self._client.table(TABLE).delete().eq("id", id).execute()
    
    async def delete_by_plato(self, plato_id: int) -> None:
        await self._client.table(TABLE).delete().eq("plato_id", plato_id).execute()
        
    async def get_by_id(self, id: int) -> PlatoIngrediente | None:
        res = (
            await self._client.table(TABLE)
            .select("*")
            .eq("id", id)
            .execute()
        )
        
        return PlatoIngrediente(**res.data[0]) if res and res.data else None
    
    async def get_by_plato(self, plato_id: int) -> list[PlatoIngrediente]:
        res = (
            await self._client.table(TABLE)
            .select("*")
            .eq("plato_id", plato_id)
            .execute()
        )
        
        return [PlatoIngrediente(**item) for item in res.data] if res and res.data else []