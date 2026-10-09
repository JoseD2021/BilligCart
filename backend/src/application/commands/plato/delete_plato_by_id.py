from dataclasses import dataclass

from src.domain.repositories.plato_repository import PlatoRepository


@dataclass(frozen=True)
class DeletePlatoByIdCommand:
    id: int

class DeletePlatoHandler:
    def __init__(self, plato:PlatoRepository):
        self._plato = plato

    async def handle(self, cmd: DeletePlatoByIdCommand) -> None:
        await self._plato.delete_by_id(cmd.id)