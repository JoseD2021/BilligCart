from dataclasses import dataclass

from domain.repositories.plato_ingrediente_repository import PlatoIngredienteRepository


@dataclass(frozen=True)
class DeletePlatoIngredienteByPlatoIdCommand:
    plato_id: int

class DeletePlatoIngredienteByPlatoIdHandler:
    def __init__(self, plt_ingr: PlatoIngredienteRepository):
            self._plato_ingrediente = plt_ingr

    async def handle(self, cmd: DeletePlatoIngredienteByPlatoIdCommand) -> None:
        await self._plato_ingrediente.delete_by_plato(cmd.plato_id)