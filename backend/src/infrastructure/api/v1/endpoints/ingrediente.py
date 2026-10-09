from fastapi import APIRouter, Depends

from src.application.commands.ingrediente.create_ingrediente import CreateIngredientCommand
from src.application.commands.ingrediente.delete_ingrediente_by_id import DeleteIngredientByIdCommand
from src.application.commands.ingrediente.update_ingrediente import UpdateIngredientCommand
from src.application.commands.ingrediente.update_fetch_ingrediente import UpdateFetchIngredientCommand
from src.application.queries.ingrediente.get_ingrediente_by_id import GetIngredientByIdQuery
from src.infrastructure.api.v1.dependencies import get_create_ingredient_handler, get_delete_ingredient_handler, get_get_ingredient_by_id_handler, get_update_ingredient_handler, get_update_fetch_ingredient_handler
from src.infrastructure.api.v1.schemas.ingrediente import CreateIngredienteBody
from src.infrastructure.api.v1.schemas.ingrediente import UpdateIngredienteBody
from src.infrastructure.api.v1.schemas.ingrediente import UpdateFetchIngredienteBody

router = APIRouter(prefix="/ingrediente", tags=["Ingrediente"])

@router.post("/create", status_code=201)
async def create_ingrediente(body: CreateIngredienteBody, handler = Depends(get_create_ingredient_handler)):
    ingrediente = await handler.handle(CreateIngredientCommand(**body.model_dump()))
    return ingrediente

@router.put("/update/{id}", status_code=200)
async def update_ingrediente(id: int, body: UpdateIngredienteBody, handler = Depends(get_update_ingredient_handler)):
    ingrediente = await handler.handle(UpdateIngredientCommand(id=id, **body.model_dump()))
    return ingrediente

@router.patch("/update/{id}/fetch", status_code=200)
async def update_fetch_ingrediente(id: int, body: UpdateFetchIngredienteBody, handler = Depends(get_update_fetch_ingredient_handler)):
    ingrediente = await handler.handle(UpdateFetchIngredientCommand(id=id, **body.model_dump()))
    return ingrediente

@router.get("/get/{id}", status_code=200)
async def get_ingrediente(id: int, handler = Depends(get_get_ingredient_by_id_handler)):
    ingrediente = await handler.handle(GetIngredientByIdQuery(id=id))
    return ingrediente

@router.delete("/delete/{id}", status_code=200)
async def delete_ingrediente(id: int, handler = Depends(get_delete_ingredient_handler)):
    await handler.handle(DeleteIngredientByIdCommand(id=id))