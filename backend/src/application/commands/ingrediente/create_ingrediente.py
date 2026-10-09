from dataclasses import dataclass

from src.domain.entities.ingrediente import Ingrediente
from src.domain.repositories.ingrediente_repository import IngredienteRepository

@dataclass(frozen=True)
class CreateIngredientCommand:
    name: str

class CreateIngredientHandler:
    def __init__(self, ingr: IngredienteRepository):
        self._ingr = ingr
        
    async def handle(self, cmd: CreateIngredientCommand) -> Ingrediente:
        ingr = Ingrediente.default(name=cmd.name)
        
        return await self._ingr.create(ingr)