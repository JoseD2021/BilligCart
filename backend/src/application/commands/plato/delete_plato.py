from dataclasses import dataclass

from domain.repositories.plato_repository import PlatoRepository


@dataclass(frozen=True)
class DeletePlatoCommand:
    id: int

class DeletePlatoHandler:
    def __init__(self, plato:PlatoRepository):
        self._plato = plato

    async def handle(self, cmd: DeletePlatoCommand) -> None:
        await self._plato.delete_plato(cmd.id)