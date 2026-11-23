from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from src.domain.enums.plato_tipo import PlatoTipo
from src.domain.errors import MenuGenerationError


@dataclass(frozen=True)
class GeneratedIngredient:
    clave: str
    nombre: str
    cantidad: float
    unidad: str

    def __post_init__(self):
        if not self.nombre.strip() or not self.unidad.strip() or not isfinite(self.cantidad) or self.cantidad <= 0:
            raise MenuGenerationError("La IA devolvió un ingrediente con nombre, unidad o cantidad inválidos.")


@dataclass(frozen=True)
class GeneratedDish:
    day: int
    tipo: PlatoTipo
    nombre: str
    ingredientes: list[GeneratedIngredient]

    def __post_init__(self):
        if not self.nombre.strip() or not self.ingredientes:
            raise MenuGenerationError("Cada comida debe tener nombre e ingredientes.")
