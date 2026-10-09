from pydantic import BaseModel

class CreatePlatoIngredienteBody(BaseModel):
    quantity: float
    unit: str
    
    plato_id: int
    ingrediente_id: int

class UpdatePlatoIngredienteBody(BaseModel):
    quantity: float
    unit: str