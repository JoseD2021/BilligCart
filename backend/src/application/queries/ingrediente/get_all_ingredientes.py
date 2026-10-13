from dataclasses import dataclass

from src.domain.entities.ingrediente import Ingrediente
from src.domain.repositories.ingrediente_repository import IngredienteRepository

class GetAllIngredientesHandler:
    def __init__(self, ingr: IngredienteRepository):
        self._ingr = ingr

    def handle(self) -> list[Ingrediente]:
        return self._ingr.get_all()
