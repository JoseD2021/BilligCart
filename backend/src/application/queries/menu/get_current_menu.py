from dataclasses import dataclass

from domain.repositories.menu_repository import MenuRepository
from domain.entities.menu import Menu

@dataclass(frozen=True)
class GetCurrentMenuQuery:
    user_id: str

class GetCurrentMenuHandler:
    def __init__(self, menu: MenuRepository):
        self._menu = menu
        
    def handle(self, query: GetCurrentMenuQuery) -> Menu | None:
        return self._menu.get_current(query.user_id)