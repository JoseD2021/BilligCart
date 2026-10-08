from dataclasses import dataclass

from domain.repositories.menu_repository import MenuRepository
from domain.entities.menu import Menu

@dataclass(frozen=True)
class GetMenuByDateQuery:
    user_id: str
    week_start: str

class GetMenuByDateHandler:
    def __init__(self, menu: MenuRepository):
        self._menu = menu
        
    def handle(self, query: GetMenuByDateQuery) -> Menu | None:
        return self._menu.get_menu_by_date(query.user_id, query.week_start)