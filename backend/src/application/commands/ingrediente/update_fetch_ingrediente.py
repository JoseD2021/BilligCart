from dataclasses import dataclass
import datetime

from src.domain.entities.ingrediente import Ingrediente, IngredienteFetchInfo
from src.domain.enums.tienda import Tienda
from src.domain.repositories.ingrediente_repository import IngredienteRepository
from src.domain.errors import InvalidRequestBodyError

@dataclass(frozen=True)
class UpdateFetchIngredientCommand:
    id: int
    
    shop: Tienda
    price: float
    url: str


class UpdateFetchIngredientHandler:
    def __init__(self, ingr: IngredienteRepository):
        self._ingr = ingr
        
    async def handle(self, cmd: UpdateFetchIngredientCommand) -> Ingrediente:
        fetch_info = IngredienteFetchInfo(
            shop=cmd.shop,
            price=cmd.price,
            url=cmd.url,
            fetched_at=datetime.datetime.now(datetime.timezone.utc),
        )
        
        if fetch_info.price < 0:
            raise InvalidRequestBodyError("Price cannot be negative")
        
        return await self._ingr.update_fetch_info(id=cmd.id, fetch_info=fetch_info)