from dataclasses import dataclass
from math import isfinite

from src.domain.errors import InvalidRequestBodyError


@dataclass(frozen=True)
class PlatoIngrediente:
    quantity: float
    unit: str

    plato_id: int
    ingrediente_id: int

    id: int | None = None

    def __post_init__(self):
        if not isfinite(self.quantity) or self.quantity <= 0 or not self.unit.strip():
            raise InvalidRequestBodyError("La cantidad debe ser positiva y la unidad es obligatoria.")
        if self.plato_id <= 0 or self.ingrediente_id <= 0:
            raise InvalidRequestBodyError("El plato y el ingrediente deben existir.")
