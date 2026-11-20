from dataclasses import dataclass

from src.domain.entities.plato import Plato
from src.domain.errors import InvalidRequestBodyError
from src.domain.repositories.plato_repository import PlatoRepository


@dataclass(frozen=True)
class GetPlatoByDayQuery:
    menu_id: int
    day: int

class GetPlatoByDayHandler:
    def __init__(self, plato: PlatoRepository):
        self._plato = plato

    async def handle(self, query: GetPlatoByDayQuery) -> list[Plato]:
        if not 1 <= query.day <= 7:
            raise InvalidRequestBodyError("El día debe estar entre 1 y 7.")
        return await self._plato.get_by_menu_day(query.menu_id, query.day)
