from dataclasses import dataclass
import datetime

from src.domain.entities.ingrediente import Ingrediente
from src.domain.repositories.ingrediente_repository import IngredienteRepository

@dataclass(frozen=True)
class UpdateIngredientCommand:
    id: int
    name: str


class UpdateIngredientHandler:
    def __init__(self, ingr: IngredienteRepository):
        self._ingr = ingr
        
    async def handle(self, cmd: UpdateIngredientCommand) -> Ingrediente:
        ingrediente = Ingrediente(
            id=cmd.id,
            name=cmd.name,
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            
            # estos son ignorados pero son necesarios para crear el objeto Ingrediente
            shop=None,
            price=None,
            url=None
        )
        
        return await self._ingr.update(ingrediente)