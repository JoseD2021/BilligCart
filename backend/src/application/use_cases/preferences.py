from src.domain.entities.preferencias import Preferencias
from src.domain.repositories.preferencias_repository import PreferenciasRepository


class PreferencesUseCase:
    def __init__(self, repository: PreferenciasRepository):
        self.repository = repository

    async def get(self, user_id: str) -> Preferencias:
        return await self.repository.get_by_user_id(user_id) or Preferencias.default(user_id)

    async def save(self, user_id: str, restricciones: list[str], presupuesto_semanal: float) -> Preferencias:
        return await self.repository.save(Preferencias(
            user_id=user_id, restricciones=restricciones, presupuesto_semanal=presupuesto_semanal,
        ))
