from dataclasses import dataclass

from src.domain.repositories.ingrediente_repository import IngredienteRepository


@dataclass(frozen=True)
class DeleteIngredientByIdCommand:
    id: int

class DeleteIngredientHandler:
    def __init__(self, ingr: IngredienteRepository):
        self._ingr = ingr

    async def handle(self, cmd: DeleteIngredientByIdCommand) -> None:
        await self._ingr.delete_by_id(cmd.id)