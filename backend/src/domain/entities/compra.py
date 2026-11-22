from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShoppingItem:
    id: str
    ingrediente_id: int
    nombre: str
    cantidad: float
    unidad: str
    supermercado: str | None
    precio: float | None


@dataclass(frozen=True)
class ShoppingList:
    menu_id: int | None
    presupuesto: float
    total: float
    items: list[ShoppingItem]
    puede_confirmar: bool
    precios_pendientes: int
