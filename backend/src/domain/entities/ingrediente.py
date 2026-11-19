import datetime
from math import isfinite
from dataclasses import dataclass

from src.domain.enums.tienda import Tienda
from src.domain.errors import InvalidRequestBodyError


@dataclass(frozen=True)
class IngredienteFetchInfo:
    shop: Tienda
    price: float
    url: str
    fetched_at: datetime.datetime

    def __post_init__(self):
        if not isfinite(self.price) or self.price < 0:
            raise InvalidRequestBodyError("El precio debe ser finito y no negativo.")

@dataclass(frozen=True)
class Ingrediente:
    name: str
    last_updated: datetime.datetime

    shop: Tienda | None
    price: float | None
    url: str | None

    id: int | None = None

    def __post_init__(self):
        if not self.name.strip():
            raise InvalidRequestBodyError("El nombre del ingrediente es obligatorio.")
        if self.price is not None and (not isfinite(self.price) or self.price < 0):
            raise InvalidRequestBodyError("El precio debe ser finito y no negativo.")

    @classmethod
    def default(cls, name: str) -> "Ingrediente":
        return cls(name=name, last_updated=datetime.datetime.now(datetime.timezone.utc), shop=None, price=None, url=None)
