from abc import ABC, abstractmethod
from datetime import date

from domain.entities.menu import Menu

class MenuRepository(ABC):
    @abstractmethod
    async def get_current(self, user_id: str) -> Menu | None:
        pass

    @abstractmethod
    async def create(self, menu: Menu) -> Menu:
        pass

    @abstractmethod
    async def update(self, menu: Menu) -> Menu:
        pass
    
    @abstractmethod
    async def get_by_date(self, user_id: str, date: date) -> Menu | None:
        pass