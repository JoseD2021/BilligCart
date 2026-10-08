from abc import ABC, abstractmethod

from domain.entities.plato import Plato

class PlatoRepository(ABC):
    @abstractmethod
    async def create_plato_for_menu(self, plato: Plato) -> Plato:
        """ Crea un plato para un menú específico """
    
    @abstractmethod
    async def update_plato(self, plato: Plato) -> Plato:
        """ Actualiza un plato existente """
        
    @abstractmethod
    async def get_platos_day(self, menu_id: int, day: int) -> list[Plato]:
        """ Obtiene todos los platos de un menú para un día específico: lunes, martes, ... """
        
    @abstractmethod
    async def delete_plato(self, id: int) -> None:
        """ Elimina un plato existente """