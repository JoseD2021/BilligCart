from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.compra import ShoppingItem

ESTADOS_PEDIDO = ("pendiente", "confirmado", "en_camino", "entregado")


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
    created_at: datetime | None = None
    ubicacion: dict | None = None  # posición en vivo del repartidor
    # Dirección de entrega que escribe el cliente: {direccion, referencia, lat, lng}.
    # En la base vive en Pedidos.direccion_dest / referencias / lat_dest / lng_dest.
    # lat/lng quedan en None hasta que el mapa/GPS del cliente los complete.
    envio: dict | None = None
    # Resuelto desde auth.users a través de repartidor_id; no se lee de Pedidos.repartidor.
    repartidor_email: str | None = None
