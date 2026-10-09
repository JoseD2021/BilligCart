from dataclasses import dataclass

@dataclass(frozen=True)
class PlatoIngrediente:
    quantity: float
    unit: str
    
    plato_id: int
    ingrediente_id: int
    
    id: int | None = None