from __future__ import annotations

from dataclasses import dataclass

from src.domain.enums.plato_tipo import PlatoTipo
from src.domain.errors import InvalidRequestBodyError


@dataclass(frozen=True)
class Plato:
    menu_id: int
    type: PlatoTipo
    name: str
    day: int # 1-7

    description: str | None = None
    id: int | None = None  # lo asigna la db

    def __post_init__(self):
        if not 1 <= self.day <= 7 or self.menu_id <= 0:
            raise InvalidRequestBodyError("El día debe estar entre 1 y 7 y el menú debe existir.")
        if not self.name.strip():
            raise InvalidRequestBodyError("El nombre del plato no puede estar vacío.")
        try:
            object.__setattr__(self, "type", PlatoTipo(self.type))
        except ValueError as exc:
            raise InvalidRequestBodyError("Tipo de comida inválido.") from exc

    @classmethod
    def default(cls, menu_id: int, type: PlatoTipo, name: str, day: int, description: str | None = None) -> Plato:
        return cls(menu_id=menu_id, type=type, name=name, day=day, description=description or None)
