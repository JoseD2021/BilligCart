from dataclasses import dataclass

from domain.repositories.plato_ingrediente_repository import PlatoIngredienteRepository


@dataclass(frozen=True)
class DeletePlatoIngredienteCommand:
    id: int

class DeletePlatoIngredienteHandler:
    def __init__(self, plt_ingr: PlatoIngredienteRepository):
            self._plato_ingrediente = plt_ingr

    async def handle(self, cmd: DeletePlatoIngredienteCommand) -> None:
        await self._plato_ingrediente.delete(cmd.id)