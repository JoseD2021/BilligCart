from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.compra import ShoppingItem


@dataclass(frozen=True)
class Pedido:
    id: str
    user_id: str
    menu_id: int
    checkout_key: str
    items: list[ShoppingItem]
    total: float
    etapa: int = 0
    repartidor_id: str | None = None
    repartidor: str | None = None
    tiempo_estimado: str | None = None
    created_at: datetime | None = None
