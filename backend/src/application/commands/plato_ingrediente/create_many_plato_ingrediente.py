from dataclasses import dataclass

from application.commands.plato_ingrediente.create_plato_ingrediente import CreatePlatoIngredienteRecetaCommand
from domain.entities.plato_ingrediente import PlatoIngrediente
from domain.repositories.plato_ingrediente_repository import PlatoIngredienteRepository

class CreateManyPlatoIngredienteCommandHandler:
    def __init__(self, plt_ingr: PlatoIngredienteRepository):
        self._plato_ingrediente = plt_ingr

    async def handle(self, cmd: list[CreatePlatoIngredienteRecetaCommand]) -> list[PlatoIngrediente]:
        rel = []
        for c in cmd:
            rel.append(PlatoIngrediente(
                quantity=c.quantity,
                unit=c.unit,
                plato_id=c.plato_id,
                ingrediente_id=c.ingrediente_id
            ))
        
        return await self._plato_ingrediente.create_many(rel)