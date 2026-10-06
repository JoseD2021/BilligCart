from pydantic import BaseModel, Field

# class ingredientsSchema(BaseMode):
#     name: str = Field(..., description="Nombre") 

class AIResponseSchema(BaseModel):
    title: str = Field(..., description="Propuesta de menu")
    ingredients: str = Field(..., description="Ingredientes")