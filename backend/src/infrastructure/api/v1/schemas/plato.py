from pydantic import BaseModel

from domain.enums.plato_tipo import PlatoTipo

class CreatePlatoBody(BaseModel):
    menu_id: int
    type: PlatoTipo
    name: str
    day: int
    description: str | None = None
    
class UpdatePlatoBody(BaseModel):
    menu_id: int
    type: PlatoTipo
    name: str
    day: int
    description: str | None = None