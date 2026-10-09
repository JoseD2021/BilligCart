from pydantic import BaseModel
from datetime import datetime

from src.domain.enums.tienda import Tienda

class CreateIngredienteBody(BaseModel):
    name: str
    
class UpdateIngredienteBody(BaseModel):
    name: str

class UpdateFetchIngredienteBody(BaseModel):
    shop: Tienda
    price: float
    url: str