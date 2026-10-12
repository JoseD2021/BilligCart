from pydantic import BaseModel

class CreateIngredienteBody(BaseModel):
    name: str
    
class UpdateIngredienteBody(BaseModel):
    name: str