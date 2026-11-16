from dataclasses import dataclass

from src.domain.entities.ingrediente import Ingrediente
from src.domain.errors import IngredienteNotFound
from src.domain.repositories.ingrediente_repository import IngredienteRepository

@dataclass(frozen=True)
class GetIngredientByIdQuery:
    id: int

class GetIngredientByIdHandler:
    def __init__(self, ingr: IngredienteRepository):
        self._ingr = ingr

    async def handle(self, query: GetIngredientByIdQuery) -> Ingrediente:
        ingrediente = await self._ingr.get_by_id(query.id)
        if ingrediente is None:
            raise IngredienteNotFound(query.id)
        return ingrediente
