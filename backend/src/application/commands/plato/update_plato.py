from dataclasses import dataclass

from domain.enums.plato_tipo import PlatoTipo
from domain.repositories.plato_repository import PlatoRepository
from domain.entities.plato import Plato

@dataclass(frozen=True)
class UpdatePlatoCommand:
    menu_id: int
    id: int
    type: PlatoTipo
    name: str
    day: int
    description: str | None = None

class UpdatePlatoHandler:
    def __init__(self, plato: PlatoRepository):
        self._plato = plato
        
    async def handle(self, cmd: UpdatePlatoCommand):
        plato = Plato(
            id=cmd.id,
            menu_id=cmd.menu_id,
            type=cmd.type,
            name=cmd.name,
            day=cmd.day,
            description=cmd.description or None,
        )
        
        await self._plato.update_plato(plato)
        return plato