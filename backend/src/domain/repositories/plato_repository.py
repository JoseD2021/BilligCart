from abc import ABC, abstractmethod

from src.domain.entities.plato import Plato

class PlatoRepository(ABC):
    @abstractmethod
    async def create(self, plato: Plato) -> Plato:
        """ Crea un plato para un menú específico """
    
    @abstractmethod
    async def update(self, plato: Plato) -> Plato:
        """ Actualiza un plato existente """
        
    @abstractmethod
    async def get_by_menu_day(self, menu_id: int, day: int) -> list[Plato]:
        """ Obtiene todos los platos de un menú para un día específico: lunes, martes, ... """
        
    @abstractmethod
    async def delete_by_id(self, id: int) -> None:
        """ Elimina un plato existente """