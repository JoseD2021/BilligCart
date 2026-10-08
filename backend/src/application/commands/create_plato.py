from dataclasses import dataclass

from domain.enums.plato_tipo import PlatoTipo
from domain.repositories.plato_repository import PlatoRepository
from domain.entities.plato import Plato

@dataclass(frozen=True)
class CreatePlatoCommand:
    menu_id: int
    type: PlatoTipo
    name: str
    day: int
    description: str | None = None

class CreatePlatoHandler:
    def __init__(self, plato: PlatoRepository):
        self._plato = plato
        
    async def handle(self, cmd: CreatePlatoCommand):
        plato = Plato.default(menu_id=cmd.menu_id, type=cmd.type, name=cmd.name, day=cmd.day, description=cmd.description)
        
        await self._plato.create_plato_for_menu(plato)
        return plato