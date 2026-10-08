from abc import ABC, abstractmethod

from domain.entities.ingrediente import IngredienteFetchInfo, Ingrediente

class IngredienteRepository(ABC):
    @abstractmethod
    async def create_ingredient(self, ingr: Ingrediente) -> Ingrediente:
        pass

    @abstractmethod
    async def update_ingredient(self, ingr: Ingrediente) -> Ingrediente:
        pass
    
    @abstractmethod
    async def update_fetch_info(self, id: int, fetch_info: IngredienteFetchInfo) -> Ingrediente:
        pass
    
    @abstractmethod
    async def get_ingredient(self, id: int) -> Ingrediente | None:
        pass
    
    @abstractmethod
    async def delete_ingredient(self, id: int) -> None:
        pass