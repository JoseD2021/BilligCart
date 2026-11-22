"""Conversión de registros de persistencia a tipos del dominio."""
from datetime import date, datetime

from src.domain.entities.ingrediente import Ingrediente
from src.domain.entities.menu import Menu
from src.domain.entities.plato import Plato
from src.domain.entities.plato_ingrediente import PlatoIngrediente
from src.domain.enums.tienda import Tienda


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value


def menu_entity(row: dict) -> Menu:
    return Menu(
        id=row["id"], user_id=str(row["user_id"]),
        week_start=date.fromisoformat(str(row["week_start"])[:10]),
        created_at=timestamp(row.get("created_at")),
    )


def plato_entity(row: dict) -> Plato:
    return Plato(**{key: row.get(key) for key in ("id", "menu_id", "type", "name", "day", "description")})


def ingrediente_entity(row: dict) -> Ingrediente:
    return Ingrediente(
        id=row["id"], name=row["name"], last_updated=timestamp(row["last_updated"]), last_fetched=timestamp(row.get("last_fetched")),
        shop=Tienda(row["shop"]) if row.get("shop") else None,
        price=float(row["price"]) if row.get("price") is not None else None,
        url=row.get("url"),
    )


def relacion_entity(row: dict) -> PlatoIngrediente:
    return PlatoIngrediente(**{key: row[key] for key in ("id", "quantity", "unit", "plato_id", "ingrediente_id")})
