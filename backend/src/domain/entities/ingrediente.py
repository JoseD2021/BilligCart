from dataclasses import dataclass
import datetime

from src.domain.enums.tienda import Tienda

@dataclass(frozen=True)
class IngredienteFetchInfo:
    shop: Tienda
    price: float
    url: str
    fetched_at: datetime.datetime

@dataclass(frozen=True)
class Ingrediente:
    name: str
    last_updated: datetime.datetime
    
    shop: Tienda | None
    price: float | None
    url: str | None
    
    id: int | None = None
    
    @classmethod
    def default(cls, name: str) -> "Ingrediente":
        return cls(name=name, last_updated=datetime.datetime.now(datetime.timezone.utc), shop=None, price=None, url=None)