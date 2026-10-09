from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.preferencias import Preferencias

class PreferenciasRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Preferencias | None: ...

    @abstractmethod
    async def save(self, preferencias: Preferencias) -> Preferencias:
        """Crea o actualiza las preferencias del usuario."""