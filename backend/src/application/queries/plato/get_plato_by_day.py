from dataclasses import dataclass

from src.domain.repositories.plato_repository import PlatoRepository
from src.domain.entities.plato import Plato

@dataclass(frozen=True)
class GetPlatoByDayQuery:
    menu_id: int
    day: int

class GetPlatoByDayHandler:
    def __init__(self, plato: PlatoRepository):
        self._plato = plato
        
    def handle(self, query: GetPlatoByDayQuery) -> list[Plato]:
        return self._plato.get_by_menu_day(query.menu_id, query.day)