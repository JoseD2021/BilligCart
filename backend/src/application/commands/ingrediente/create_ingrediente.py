from dataclasses import dataclass

from domain.entities.ingrediente import Ingrediente
from domain.repositories.ingrediente_repository import IngredienteRepository

@dataclass(frozen=True)
class CreateIngredientCommand:
    name: str

class CreateIngredientHandler:
    def __init__(self, ingr: IngredienteRepository):
        self._ingr = ingr
        
    async def handle(self, cmd: CreateIngredientCommand) -> Ingrediente:
        ingr = Ingrediente.default(name=cmd.name)
        
        return await self._ingr.create_ingredient(ingr)