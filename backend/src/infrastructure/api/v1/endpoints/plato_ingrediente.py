from fastapi import APIRouter, Depends

from application.commands.plato_ingrediente.create_plato_ingrediente import CreatePlatoIngredienteRecetaCommand
from application.commands.plato_ingrediente.update_plato_ingrediente import UpdatePlatoIngredienteRecetaCommand
from application.commands.plato_ingrediente.delete_plato_ingrediente import DeletePlatoIngredienteCommand
from application.commands.plato_ingrediente.delete_plato_ingrediente_by_platoid import DeletePlatoIngredienteByPlatoIdCommand
from application.queries.plato_ingrediente.get_plato_ingrediente_by_platoid import GetPlatoIngredienteByPlatoIdQuery
from application.queries.plato_ingrediente.get_plato_ingrediente_by_id import GetPlatoIngredienteByIdQuery
from infrastructure.api.v1.dependencies import get_create_many_plato_ingrediente_handler, get_create_plato_ingrediente_handler, get_delete_plato_ingrediente_by_plato_id_handler, get_delete_plato_ingrediente_handler, get_get_plato_ingrediente_by_id_handler, get_get_plato_ingrediente_by_plato_id_handler, get_update_plato_ingrediente_handler
from infrastructure.api.v1.schemas.plato_ingrediente import CreatePlatoIngredienteBody, UpdatePlatoIngredienteBody
from domain.entities.plato_ingrediente import PlatoIngrediente

router = APIRouter(prefix="/plato-ingrediente", tags=["PlatoIngrediente"])
    
@router.post("/create")
async def create_plato_ingrediente(body: CreatePlatoIngredienteBody, handler = Depends(get_create_plato_ingrediente_handler)) -> PlatoIngrediente:
    rel = await handler.handle(CreatePlatoIngredienteRecetaCommand(**body.model_dump()))
    return rel

@router.post("/create-many")
async def create_many_plato_ingrediente(body: list[CreatePlatoIngredienteBody], handler = Depends(get_create_many_plato_ingrediente_handler)) -> list[PlatoIngrediente]:
    rel = await handler.handle([CreatePlatoIngredienteRecetaCommand(**b.model_dump()) for b in body])
    return rel

@router.patch("/update/{id}")
async def update_plato_ingrediente(id: int, body: UpdatePlatoIngredienteBody, handler = Depends(get_update_plato_ingrediente_handler)) -> PlatoIngrediente:
    rel = await handler.handle(UpdatePlatoIngredienteRecetaCommand(id=id, **body.model_dump()))
    return rel

@router.get("/get/{id}")
async def get_plato_ingrediente(id: int, handler = Depends(get_get_plato_ingrediente_by_id_handler)) -> PlatoIngrediente:
    rel = await handler.handle(GetPlatoIngredienteByIdQuery(id=id))
    return rel

@router.get("/get-by-plato/{plato_id}")
async def get_plato_ingrediente_by_plato(plato_id: int, handler = Depends(get_get_plato_ingrediente_by_plato_id_handler)) -> list[PlatoIngrediente]:
    rel = await handler.handle(GetPlatoIngredienteByPlatoIdQuery(plato_id=plato_id))
    return rel

@router.delete("/delete/{id}")
async def delete_plato_ingrediente(id: int, handler = Depends(get_delete_plato_ingrediente_handler)):
    return await handler.handle(DeletePlatoIngredienteCommand(id=id))


@router.delete("/delete-by-plato/{plato_id}")
async def delete_plato_ingrediente_by_plato(plato_id: int, handler = Depends(get_delete_plato_ingrediente_by_plato_id_handler)):
    return await handler.handle(DeletePlatoIngredienteByPlatoIdCommand(plato_id=plato_id))