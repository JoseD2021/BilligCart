from abc import ABC, abstractmethod
from datetime import date

from domain.entities.menu import Menu

class MenuRepository(ABC):
    @abstractmethod
    async def get_current_menu(self, user_id: str) -> Menu | None:
        pass

    @abstractmethod
    async def create_menu(self, menu: Menu) -> Menu:
        pass

    @abstractmethod
    async def update_menu(self, menu: Menu) -> Menu:
        pass
    
    @abstractmethod
    async def get_menu_by_date(self, user_id: str, date: date) -> Menu | None:
        pass