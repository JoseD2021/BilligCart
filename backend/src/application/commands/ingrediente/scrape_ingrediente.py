import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.application.commands.ingrediente.update_fetch_ingrediente import (
    UpdateFetchIngredientCommand,
    UpdateFetchIngredientHandler,
)
from src.application.interfaces.fetcher import Fetcher
from src.application.interfaces.scraper_builder import ScraperBuilder
from src.application.scraping.director_scraping import DirectorScraping
from src.domain.entities.ingrediente import Ingrediente
from src.domain.errors import (
    IngredienteNotFound,
    IngredienteRecentlyUpdated,
    NoOffersFound,
    ScrapingError,
)
from src.domain.repositories.ingrediente_repository import IngredienteRepository


@dataclass(frozen=True)
class ScrapeIngredienteCommand:
    id: int

class ScrapeIngredienteHandler:
    _DAYS_TO_UPDATE = 7

    def __init__(self, ingr: IngredienteRepository, fetcher: Fetcher, builders: list[ScraperBuilder], update_fetch: UpdateFetchIngredientHandler):
        self._ingr = ingr
        self._fetcher = fetcher
        self._builders = builders
        self._update_fetch = update_fetch

    async def handle(self, cmd: ScrapeIngredienteCommand) -> Ingrediente:
        ing = await self._ingr.get_by_id(cmd.id)
        if ing is None:
            raise IngredienteNotFound(cmd.id)

        last_updated = ing.last_updated
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=UTC)

        if ing.shop is not None and (datetime.now(UTC) - last_updated) < timedelta(days=self._DAYS_TO_UPDATE):
            raise IngredienteRecentlyUpdated(cmd.id, last_updated)

        ofertas = [o for r in await asyncio.gather(
            *(self._buscar(builder=b, termino=ing.name, limit=5) for b in self._builders)
        ) for o in r]

        if not ofertas:
            raise NoOffersFound(ing.name)

        mejor: Ingrediente = min(ofertas, key=lambda p: p.price)
        return await self._update_fetch.handle(UpdateFetchIngredientCommand(
            id=cmd.id, shop=mejor.shop, price=mejor.price, url=mejor.url,
        ))

    async def _buscar(self, builder: ScraperBuilder, termino: str, limit: int = 5) -> list[Ingrediente]:
        try:
            b: ScraperBuilder = builder()
            raw = await self._fetcher.fetch(b.url_search(termino=termino, limit=limit))

            return DirectorScraping(builder).process_list(raw)
        except ScrapingError as e:
            logging.getLogger(__name__).warning("Error al buscar ofertas con %s: %s", builder.__name__, e)

            return []
