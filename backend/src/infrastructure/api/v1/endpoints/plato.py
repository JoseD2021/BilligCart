from fastapi import APIRouter, Depends, Query

from src.application.commands.plato.create_plato import CreatePlatoCommand
from src.application.commands.plato.delete_plato_by_id import DeletePlatoByIdCommand
from src.application.commands.plato.update_plato import UpdatePlatoCommand
from src.application.queries.plato.get_plato_by_day import GetPlatoByDayQuery
from src.infrastructure.api.v1.dependencies import (
    get_access_policy,
    get_create_plato_handler,
    get_current_user,
    get_delete_plato_handler,
    get_plato_by_day_handler,
    get_update_plato_handler,
)
from src.infrastructure.api.v1.schemas.plato import CreatePlatoBody, UpdatePlatoBody

router = APIRouter(prefix="/plato", tags=["Plato"], dependencies=[Depends(get_current_user)])

@router.post("/create", status_code=201)
async def create_plato(body: CreatePlatoBody, handler = Depends(get_create_plato_handler), user=Depends(get_current_user), access=Depends(get_access_policy)):
    await access.menu(user, body.menu_id)
    plato = await handler.handle(CreatePlatoCommand(**body.model_dump()))
    return plato

@router.put("/update/{id}", status_code=200)
async def update(body: UpdatePlatoBody, id: int, handler = Depends(get_update_plato_handler), user=Depends(get_current_user), access=Depends(get_access_policy)):
    await access.plato(user, id)
    await access.menu(user, body.menu_id)
    plato = await handler.handle(UpdatePlatoCommand(id=id, **body.model_dump()))
    return plato

@router.get("/day/{day}", status_code=200)
async def get_platos_by_day(day: int, menu_id: int = Query(..., description="id del menu"), handler = Depends(get_plato_by_day_handler), user=Depends(get_current_user), access=Depends(get_access_policy)):
    await access.menu(user, menu_id)
    platos = await handler.handle(GetPlatoByDayQuery(menu_id=menu_id, day=day))
    return platos

@router.delete("/delete/{id}", status_code=200)
async def delete_by_id(id: int, handler = Depends(get_delete_plato_handler), user=Depends(get_current_user), access=Depends(get_access_policy)):
    await access.plato(user, id)
    await handler.handle(DeletePlatoByIdCommand(id=id))
