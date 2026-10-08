from dataclasses import dataclass

from domain.repositories.ingrediente_repository import IngredienteRepository


@dataclass(frozen=True)
class DeleteIngredientCommand:
    id: int

class DeleteIngredientHandler:
    def __init__(self, ingr: IngredienteRepository):
        self._ingr = ingr

    async def handle(self, cmd: DeleteIngredientCommand) -> None:
        await self._ingr.delete_ingredient(cmd.id)