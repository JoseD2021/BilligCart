from dataclasses import dataclass

from domain.entities.plato_ingrediente import PlatoIngrediente
from domain.repositories.plato_ingrediente_repository import PlatoIngredienteRepository

@dataclass(frozen=True)
class UpdatePlatoIngredienteRecetaCommand:
    quantity: float
    unit: str
    
    id: int
    
class UpdatePlatoIngredienteCommandHandler:
    def __init__(self, plt_ingr: PlatoIngredienteRepository):
        self._plato_ingrediente = plt_ingr

    async def handle(self, cmd: UpdatePlatoIngredienteRecetaCommand) -> PlatoIngrediente:
        rel = PlatoIngrediente(
            quantity=cmd.quantity,
            unit=cmd.unit,
            id=cmd.id,
            
            # no son usados en la actualización, pero son necesarios para crear la instancia de PlatoIngrediente
            plato_id=0,
            ingrediente_id=0
        )
        
        return await self._plato_ingrediente.update(rel)