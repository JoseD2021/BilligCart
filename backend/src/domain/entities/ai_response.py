from pydantic import BaseModel, Field

class ingredientsSchema(BaseModel):
    name: str = Field(..., description="Nombre del ingrediente") 
    cantidad: float = Field(..., description="Cantidad de ingrediente necesaria por unidad")
    unit: str = Field(..., description="Unidad de medida") 

class ComidaSchema(BaseModel):
    name: str = Field(..., description="Nombre de la comida")
    ingredients: list[ingredientsSchema] = Field(..., description="Ingredientes")

class DiaSchema(BaseModel):
    desayuno: ComidaSchema = Field(..., description="desayuno")
    almuerzo: ComidaSchema = Field(..., description="almuerzo")
    cena: ComidaSchema = Field(..., description="cena")

class menu(BaseModel):
    lunes: DiaSchema = Field(...,description="Comidas del lunes")
    martes: DiaSchema = Field(...,description="Comidas del martes")
    miercoles: DiaSchema = Field(...,description="Comidas del miercoles")
    jueves: DiaSchema = Field(...,description="Comidas del jueves")
    viernes: DiaSchema = Field(...,description="Comidas del viernes")
    sabado: DiaSchema = Field(...,description="Comidas del sabado")
    domingo: DiaSchema = Field(...,description="Comidas del domingo")

class AIResponseSchema(BaseModel):
    menuSemanal: menu = Field(..., description="Menu semanal")