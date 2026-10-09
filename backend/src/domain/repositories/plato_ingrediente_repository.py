from abc import ABC, abstractmethod

from domain.entities.plato_ingrediente import PlatoIngrediente

class PlatoIngredienteRepository(ABC):
    @abstractmethod
    async def create(self, plato_ingrediente: PlatoIngrediente) -> PlatoIngrediente:
        """Relaciona un plato con un ingrediente (con cantidad y unidad)."""

    @abstractmethod
    async def create_many(self, items: list[PlatoIngrediente]) -> list[PlatoIngrediente]:
        """Relaciona varios ingredientes con un plato en una sola operación."""

    @abstractmethod
    async def update(self, plato_ingrediente: PlatoIngrediente) -> PlatoIngrediente:
        """Actualiza cantidad/unidad de una relación existente."""

    @abstractmethod
    async def get_by_id(self, id: int) -> PlatoIngrediente | None:
        """Obtiene una relación por su id."""

    @abstractmethod
    async def get_by_plato(self, plato_id: int) -> list[PlatoIngrediente]:
        """Obtiene todos los ingredientes de un plato."""

    @abstractmethod
    async def delete_by_id(self, id: int) -> None:
        """Elimina una relación."""

    @abstractmethod
    async def delete_by_plato(self, plato_id: int) -> None:
        """Elimina todos los ingredientes de un plato."""