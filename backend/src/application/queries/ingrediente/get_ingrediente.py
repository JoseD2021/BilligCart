from dataclasses import dataclass

from domain.entities.ingrediente import Ingrediente
from domain.repositories.ingrediente_repository import IngredienteRepository

@dataclass(frozen=True)
class GetIngredientByIdQuery:
    id: int

class GetIngredientByIdHandler:
    def __init__(self, ingr: IngredienteRepository):
        self._ingr = ingr
        
    def handle(self, query: GetIngredientByIdQuery) -> Ingrediente | None:
        return self._ingr.get_ingredient(query.id)