import asyncio

from realtime import dataclass
from datetime import datetime, timezone

from src.domain.repositories.ingrediente_repository import IngredienteRepository
from src.application.interfaces.fetcher import Fetcher
from src.application.commands.ingrediente.update_fetch_ingrediente import UpdateFetchIngredientCommand, UpdateFetchIngredientHandler
from src.application.scraping.director_scraping import DirectorScraping
from src.application.interfaces.scraper_builder import ScraperBuilder
from src.domain.entities.ingrediente import Ingrediente
from src.domain.errors import IngredienteNotFound, NoOffersFound, ScrapingError, IngredienteRecentlyUpdated

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
        
        if ing.last_updated is not None and ing.shop is not None:
            lastUpdateDiff = datetime.strptime(ing.last_updated, "%Y-%m-%dT%H:%M:%S.%f%z") - datetime.now(timezone.utc)
            
            if lastUpdateDiff.days < self._DAYS_TO_UPDATE:
                raise IngredienteRecentlyUpdated(cmd.id, ing.last_updated)

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
            print(f"Error al buscar en {builder.__class__.__name__}: {e}")

            return []