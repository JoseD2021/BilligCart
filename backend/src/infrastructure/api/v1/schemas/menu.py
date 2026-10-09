from pydantic import BaseModel

class UpdateMenuBody(BaseModel):
    user_id: str
    menu_id: int
