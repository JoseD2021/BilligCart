import datetime
import json
from urllib.parse import quote

from src.domain.entities.ingrediente import Ingrediente
from src.domain.errors import ScrapingError
from src.application.interfaces.scraper_builder import ScraperBuilder
from src.domain.enums.tienda import Tienda


class ScraperOlimpica(ScraperBuilder):
    tienda = Tienda.Olimpica
    _BASE = "https://www.olimpica.com"
    _SELLER_PROPIO = '1'

    def url_search(self, termino: str, limit: int = 10) -> str:
        return (f"{self._BASE}/api/catalog_system/pub/products/search"
                f"?ft={quote(termino)}&_from=0&_to={limit - 1}")

    def reset(self) -> None:
        self._items: list[tuple[dict, dict]] = []
        self._actual: tuple[dict, dict] | None = None
        self._datos: dict = {}

    def load_content(self, raw: str) -> None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ScrapingError("Olimpica: respuesta no es JSON") from e
        if not isinstance(data, list):
            raise ScrapingError("Olimpica: se esperaba una lista de productos")

        for producto in data:
            oferta = self._oferta_disponible(producto)
            #print(f"oferta: {oferta}")
            
            if oferta:
                self._items.append((producto, oferta))

    def total_res(self) -> int:
        return len(self._items)

    def select_res(self, i: int) -> None:
        self._actual = self._items[i]
        self._datos = {}

    def extract_name(self) -> None:
        self._datos["nombre"] = self._actual[0].get("productName", "").strip()

    def extract_price(self) -> None:
        self._datos["precio"] = float(self._actual[1]["Price"])

    def extract_url(self) -> None:
        self._datos["url"] = self._actual[0].get("link", "")

    def get(self) -> Ingrediente:
        d = self._datos
        if d.get("nombre") is None or d.get("precio") is None or d.get("url") is None:
            raise ScrapingError("Olimpica: producto incompleto (posible cambio de estructura en la pagina)", d)
        return Ingrediente(
            name=d["nombre"], last_updated=datetime.datetime.now(datetime.timezone.utc),
            price=d["precio"], shop=self.tienda, url=d["url"],
        )

    # --- helpers ---
    def _oferta_disponible(self, producto: dict) -> dict | None:
        for item in producto.get("items", []):
            #print(f"item: {item}")
            for seller in item.get("sellers", []):
                #print(f"seller: {seller}")
                if seller.get("sellerId") != self._SELLER_PROPIO:
                    continue
                oferta = seller.get("commertialOffer") or {}
                if oferta.get("IsAvailable") and (oferta.get("Price") or 0) > 0:
                    print(f"[OLIMPICA] Oferta disponible: {producto['productName']} ${oferta['Price']} ({producto['link']})")
                    return oferta
        return None