from dataclasses import dataclass

from domain.entities.menu import Menu
from domain.repositories.menu_repository import MenuRepository

@dataclass(frozen=True)
class CreateMenuCommand:
    user_id: str

class CreateMenuHandler:
    def __init__(self, menu: MenuRepository):
        self._menu = menu

    async def handle(self, cmd: CreateMenuCommand) -> Menu:
        menu = Menu.default(user_id=cmd.user_id)
        await self._menu.create(menu)
        return menu