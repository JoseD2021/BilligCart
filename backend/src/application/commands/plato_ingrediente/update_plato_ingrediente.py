from dataclasses import dataclass

from src.domain.entities.plato_ingrediente import PlatoIngrediente
from src.domain.errors import ResourceNotFound
from src.domain.repositories.plato_ingrediente_repository import (
    PlatoIngredienteRepository,
)


@dataclass(frozen=True)
class UpdatePlatoIngredienteRecetaCommand:
    quantity: float
    unit: str

    id: int

class UpdatePlatoIngredienteCommandHandler:
    def __init__(self, plt_ingr: PlatoIngredienteRepository):
        self._plato_ingrediente = plt_ingr

    async def handle(self, cmd: UpdatePlatoIngredienteRecetaCommand) -> PlatoIngrediente:
        original = await self._plato_ingrediente.get_by_id(cmd.id)
        if original is None:
            raise ResourceNotFound("Relación no encontrada.")
        rel = PlatoIngrediente(
            quantity=cmd.quantity,
            unit=cmd.unit,
            id=cmd.id,

            plato_id=original.plato_id,
            ingrediente_id=original.ingrediente_id
        )

        return await self._plato_ingrediente.update(rel)
