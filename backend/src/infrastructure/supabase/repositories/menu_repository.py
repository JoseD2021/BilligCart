import datetime
from uuid import UUID

from supabase import AsyncClient

from src.domain.entities.menu import Menu
from src.infrastructure.supabase.repositories.mappers import menu_entity

TABLE = "Menu"

class SupabaseMenuRepository(MenuRepository):
    def __init__(self, client: AsyncClient):
        self._client = client

    async def get_current(self, user_id: str):
        res = (
            await self._client.table(TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .eq("week_start", Menu.default(user_id).week_start.isoformat())  # Obtener el menú de la semana actual
            .execute()
        )

        return menu_entity(res.data[0]) if res and res.data else None

    async def create(self, menu: Menu):
        payload = {"user_id": str(menu.user_id), "week_start": menu.week_start.isoformat()}
        # si ya tiene id (update), se incluye, si no, la db lo asigna
        if menu.id is not None:
            payload["id"] = menu.id

        res = (
            await self._client.table(TABLE)
            .upsert(payload, on_conflict="user_id")
            .execute()
        )
        return menu_entity(res.data[0])

    async def get_by_id(self, id: int) -> Menu | None:
        res = await self._client.table(TABLE).select("*").eq("id", id).execute()
        return menu_entity(res.data[0]) if res and res.data else None

    async def get_by_date(self, user_id: str, date: datetime.date) -> Menu | None:
        # calc lunes a las 00:00
        try:
            week_start = date - datetime.timedelta(days=date.weekday())
            week_start = week_start.strftime("%Y-%m-%d")

            res = (
                await self._client.table(TABLE)
                .select("*")
                .eq("user_id", str(user_id))
                .eq("week_start", week_start)
                .execute()
            )
            return menu_entity(res.data[0]) if res and res.data else None
        except ValueError:
            return None
