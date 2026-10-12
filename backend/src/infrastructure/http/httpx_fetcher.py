import httpx
from src.application.interfaces.fetcher import Fetcher
from src.domain.errors import ScrapingError

class HttpxFetcher(Fetcher):
    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client or httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
                "Accept-Language": "es-CO,es;q=0.9",
            },
        )

    async def fetch(self, url: str) -> str:
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as e:
            raise ScrapingError(f"No se pudo obtener {url}: {e}") from e

    async def aclose(self) -> None:
        await self._client.aclose()