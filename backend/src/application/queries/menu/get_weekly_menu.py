import asyncio

from src.domain.errors import ResourceNotFound
from src.domain.repositories.ingrediente_repository import IngredienteRepository
from src.domain.repositories.menu_repository import MenuRepository
from src.domain.repositories.plato_ingrediente_repository import (
    PlatoIngredienteRepository,
)
from src.domain.repositories.plato_repository import PlatoRepository

DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")


class GetWeeklyMenu:
    def __init__(self, menus: MenuRepository, platos: PlatoRepository,
                 ingredientes: IngredienteRepository, relaciones: PlatoIngredienteRepository):
        self.menus, self.platos = menus, platos
        self.ingredientes, self.relaciones = ingredientes, relaciones

    async def execute(self, user_id: str) -> dict | None:
        menu = await self.menus.get_current(user_id)
        if menu is None:
            return None
        grupos = await asyncio.gather(*(self.platos.get_by_menu_day(menu.id, day) for day in range(1, 8)))
        platos = [plato for grupo in grupos for plato in grupo]
        if not platos:
            return None
        relaciones = await asyncio.gather(*(self.relaciones.get_by_plato(p.id) for p in platos))
        ids = {r.ingrediente_id for grupo in relaciones for r in grupo}
        ingredientes = dict(zip(ids, await asyncio.gather(*(self.ingredientes.get_by_id(i) for i in ids))))
        dias = [{"dia": dia, "comidas": {}} for dia in DIAS]
        for plato, grupo in zip(platos, relaciones):
            items = []
            for rel in grupo:
                ingrediente = ingredientes[rel.ingrediente_id]
                if ingrediente is None:
                    raise ResourceNotFound("Falta un ingrediente del menú.")
                items.append({
                    "id": ingrediente.id, "nombre": ingrediente.name, "cantidad": rel.quantity,
                    "unidad": rel.unit, "precio": ingrediente.price, "tienda": ingrediente.shop,
                    "ultimo_fetch": ingrediente.last_fetched.isoformat() if ingrediente.last_fetched else None,
                })
            dias[plato.day - 1]["comidas"][plato.type.value.lower()] = {
                "id": plato.id, "nombre": plato.name, "descripcion": plato.description, "ingredientes": items,
            }
        return {"id": menu.id, "semanaInicio": menu.week_start.isoformat(), "dias": dias}
