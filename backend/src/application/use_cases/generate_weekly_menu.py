import asyncio
import logging

from src.application.use_cases.preferences import PreferencesUseCase
from src.application.use_cases.persist_generated_menu import PersistGeneratedMenuUseCase
from src.application.queries.menu.get_weekly_menu import GetWeeklyMenu
from src.domain.repositories.ai_client_interface import AIClientInterface


logger = logging.getLogger(__name__)


class GenerateWeeklyMenu:
    def __init__(self, preferences: PreferencesUseCase, ai: AIClientInterface,
                 persistence: PersistGeneratedMenuUseCase, weekly_menu: GetWeeklyMenu):
        self.preferences, self.ai = preferences, ai
        self.persistence, self.weekly_menu = persistence, weekly_menu

    async def execute(self, user_id: str):
        prefs = await self.preferences.get(user_id)
        prompt = " ".join((
            f"Restricciones alimentarias: {', '.join(prefs.restricciones) or 'ninguna'}.",
            f"Presupuesto semanal: {prefs.presupuesto_semanal:.0f} COP." if prefs.presupuesto_semanal else "",
            "Genera un desayuno, un almuerzo y una cena distintos de lunes a domingo para una persona.",
            "Usa ingredientes genéricos, sin marcas, disponibles en supermercados de Colombia.",
            "Expresa cantidades positivas en g, ml o unidad. Responde en español.",
        ))
        logger.info("menu_generation_requested user_id=%s", user_id)
        response = await asyncio.to_thread(self.ai.generate_response, prompt, user_id)
        await self.persistence.execute(user_id, response)
        logger.info("menu_generation_persisted user_id=%s", user_id)
        return await self.weekly_menu.execute(user_id)
