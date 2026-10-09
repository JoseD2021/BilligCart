from dataclasses import dataclass

from domain.entities.plato_ingrediente import PlatoIngrediente
from domain.repositories.plato_ingrediente_repository import PlatoIngredienteRepository

@dataclass(frozen=True)
class CreatePlatoIngredienteRecetaCommand:
    quantity: float
    unit: str
    
    plato_id: int
    ingrediente_id: int
    
class CreatePlatoIngredienteCommandHandler:
    def __init__(self, plt_ingr: PlatoIngredienteRepository):
        self._plato_ingrediente = plt_ingr

    async def handle(self, cmd: CreatePlatoIngredienteRecetaCommand) -> PlatoIngrediente:
        rel = PlatoIngrediente(
            quantity=cmd.quantity,
            unit=cmd.unit,
            plato_id=cmd.plato_id,
            ingrediente_id=cmd.ingrediente_id
        )
        
        return await self._plato_ingrediente.create(rel)