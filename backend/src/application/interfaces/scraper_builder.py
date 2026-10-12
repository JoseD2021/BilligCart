from abc import ABC, abstractmethod

from src.domain.enums.tienda import Tienda
from src.domain.entities.ingrediente import Ingrediente

class ScraperBuilder(ABC):
    tienda: Tienda
    _BASE: str

    @abstractmethod
    def url_search(self, termino: str, limit: int = 10) -> str: ...
    @abstractmethod
    def reset(self) -> None: ...
    @abstractmethod
    def load_content(self, raw: str) -> None: ...
    @abstractmethod
    def total_res(self) -> int: ...
    @abstractmethod
    def select_res(self, i: int) -> None: ...   # fija el nodo actual
    @abstractmethod
    def extract_name(self) -> None: ...
    @abstractmethod
    def extract_price(self) -> None: ...
    @abstractmethod
    def extract_url(self) -> None: ...
    @abstractmethod
    def get(self) -> Ingrediente: ...