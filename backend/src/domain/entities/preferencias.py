from dataclasses import dataclass, field
from math import isfinite

from src.domain.errors import InvalidRequestBodyError

@dataclass(frozen=True)
class Preferencias:
    user_id: str
    id: int | None = None  # lo asigna la db
    restricciones: list[str] = field(default_factory=list)
    presupuesto_semanal: float = 0

    def __post_init__(self):
        if not isfinite(self.presupuesto_semanal) or self.presupuesto_semanal < 0:
            raise InvalidRequestBodyError("El presupuesto debe ser un número mayor o igual a cero.")
        if any(not r.strip() for r in self.restricciones):
            raise InvalidRequestBodyError("Las restricciones no pueden estar vacías.")

    @classmethod
    def default(cls, user_id: str) -> "Preferencias":
        return cls(user_id=user_id)
