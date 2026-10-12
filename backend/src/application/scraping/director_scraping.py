from src.application.interfaces.scraper_builder import ScraperBuilder
from src.domain.entities.ingrediente import Ingrediente

class DirectorScraping:
    def __init__(self, builder: ScraperBuilder):
        self._builder = builder

    def process_list(self, raw: str, limit: int = 5) -> list[Ingrediente]:
        b: ScraperBuilder = self._builder()
        b.reset()
        b.load_content(raw)
        productos = []
        for i in range(min(limit, b.total_res())):
            b.select_res(i)
            b.extract_name()
            b.extract_price()
            b.extract_url()
            productos.append(b.get())
        return productos