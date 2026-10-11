from abc import ABC, abstractmethod

class Fetcher(ABC):
    @abstractmethod
    async def fetch(self, url: str) -> str:
        """Devuelve el resultado de la URL."""