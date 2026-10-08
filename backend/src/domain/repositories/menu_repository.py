from abc import ABC, abstractmethod

from domain.entities.menu import Menu

class MenuRepository(ABC):
    @abstractmethod
    def get_current_menu(self, user_id: str) -> Menu | None:
        pass

    @abstractmethod
    def create_menu(self, menu: Menu) -> Menu:
        pass

    @abstractmethod
    def update_menu(self, menu: Menu) -> Menu:
        pass
    
    @abstractmethod
    def get_menu_by_date(self, user_id: str, date: str) -> Menu | None:
        pass