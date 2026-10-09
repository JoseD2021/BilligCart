from abc import ABC, abstractmethod

from domain.entities.ingrediente import IngredienteFetchInfo, Ingrediente

class IngredienteRepository(ABC):
    @abstractmethod
    async def create(self, ingr: Ingrediente) -> Ingrediente:
        pass

    @abstractmethod
    async def update(self, ingr: Ingrediente) -> Ingrediente:
        pass
    
    @abstractmethod
    async def update_fetch_info(self, id: int, fetch_info: IngredienteFetchInfo) -> Ingrediente:
        pass
    
    @abstractmethod
    async def get_by_id(self, id: int) -> Ingrediente | None:
        pass
    
    @abstractmethod
    async def delete_by_id(self, id: int) -> None:
        pass