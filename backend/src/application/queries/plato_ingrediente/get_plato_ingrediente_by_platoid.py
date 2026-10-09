from dataclasses import dataclass

from src.domain.repositories.plato_ingrediente_repository import PlatoIngredienteRepository
from src.domain.entities.plato import Plato

@dataclass(frozen=True)
class GetPlatoIngredienteByPlatoIdQuery:
    plato_id: int

class GetPlatoIngredienteByPlatoIdHandler:
    def __init__(self, plato_ingrediente: PlatoIngredienteRepository):
        self._plato_ingrediente = plato_ingrediente
        
    def handle(self, query: GetPlatoIngredienteByPlatoIdQuery) -> list[Plato]:
        return self._plato_ingrediente.get_by_plato(query.plato_id)