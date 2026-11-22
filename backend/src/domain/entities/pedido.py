from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.compra import ShoppingItem

ESTADOS_PEDIDO = ("pendiente", "confirmado", "en_camino", "entregado")
ETAPA_POR_ESTADO = {estado: i for i, estado in enumerate(ESTADOS_PEDIDO)}


@dataclass(frozen=True)
class Pedido:
    id: str
    user_id: str
    menu_id: int
    checkout_key: str
    items: list[ShoppingItem]
    total: float
    estado: str = "pendiente"
    repartidor_id: str | None = None
    repartidor: str | None = None
    tiempo_estimado: str | None = None
    created_at: datetime | None = None
    ubicacion: dict | None = None

    @property
    def etapa(self) -> int:
        return ETAPA_POR_ESTADO.get(self.estado, 0)
