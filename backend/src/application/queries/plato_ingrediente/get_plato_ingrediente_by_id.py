from dataclasses import dataclass

from domain.repositories.plato_ingrediente_repository import PlatoIngredienteRepository
from domain.entities.plato import Plato

@dataclass(frozen=True)
class GetPlatoIngredienteByIdQuery:
    id: int

class GetPlatoIngredienteByIdHandler:
    def __init__(self, plato_ingrediente: PlatoIngredienteRepository):
        self._plato_ingrediente = plato_ingrediente
        
    def handle(self, query: GetPlatoIngredienteByIdQuery) -> list[Plato]:
        return self._plato_ingrediente.get_by_id(query.id)