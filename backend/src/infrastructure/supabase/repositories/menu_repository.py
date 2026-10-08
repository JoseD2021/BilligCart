from uuid import UUID
import datetime

from supabase import AsyncClient

from domain.repositories.menu_repository import MenuRepository
from domain.entities.menu import Menu

TABLE = "Menu"

class SupabaseMenuRepository(MenuRepository):
    def __init__(self, client: AsyncClient):
        self._client = client

    async def get_current_menu(self, user_id: str):
        res = (
            await self._client.table(TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .eq("week_start", Menu.default(user_id).week_start)  # Obtener el menú de la semana actual
            .execute()
        )
        
        return self._to_entity(res.data[0]) if res and res.data else None

    async def create_menu(self, menu: Menu):
        payload = {"user_id": str(menu.user_id), "week_start": menu.week_start}
        # si ya tiene id (update), se incluye, si no, la db lo asigna
        if menu.id is not None:
            payload["id"] = menu.id

        res = (
            await self._client.table(TABLE)
            .upsert(payload, on_conflict="user_id")
            .execute()
        )
        return self._to_entity(res.data[0])

    async def update_menu(self, user_id: str, menu_id: int, menu_data: dict):
        # Lógica para actualizar el menú del usuario en Supabase
        pass
    
    async def get_menu_by_date(self, user_id: str, date: str):
        # calc lunes a las 00:00
        try:
            d = datetime.datetime.strptime(date, "%Y-%m-%d")
            week_start = d - datetime.timedelta(days=d.weekday())
            week_start = week_start.strftime("%Y-%m-%d")
            
            res = (
                await self._client.table(TABLE)
                .select("*")
                .eq("user_id", str(user_id))
                .eq("week_start", week_start)
                .execute()
            )
            return self._to_entity(res.data[0]) if res and res.data else None
        except ValueError:
            return None
    @staticmethod
    def _to_entity(row: dict) -> Menu:
        return Menu(id=row["id"], user_id=UUID(row["user_id"]), week_start=row["week_start"], created_at=row["created_at"])