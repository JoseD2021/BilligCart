from fastapi import APIRouter, Depends, Query
from datetime import date

from application.commands.menu.create_menu import CreateMenuCommand
from application.queries.menu.get_current_menu import GetCurrentMenuQuery
from application.queries.menu.get_menu_by_date import GetMenuByDateQuery
from infrastructure.api.v1.dependencies import get_current_user, get_create_menu_handler, get_current_menu_handler, get_menu_by_date_handler
from infrastructure.api.v1.schemas.menu import UpdateMenuBody


router = APIRouter(prefix="/menu", tags=["Menu"])


@router.get("/current", status_code=200)
async def get_current_menu(current_user=Depends(get_current_user), handler=Depends(get_current_menu_handler)):
    # Lógica para obtener el menú actual del usuario autenticado
    menu = await handler.handle(GetCurrentMenuQuery(user_id=current_user.id))
    return menu

# Llamada a Ollama, etc etc...
@router.post("/create", status_code=201)
async def create_menu(current_user=Depends(get_current_user), handler=Depends(get_create_menu_handler)):
    menu = await handler.handle(CreateMenuCommand(user_id=current_user.id))
    return menu

@router.put("/update", status_code=200) # TODO: deberia el usuario poder actualizar el menu? o simplemente crear uno nuevo? un solo plato en vez de todo el menu?
async def update_menu(body: UpdateMenuBody):
    # Lógica para actualizar el menú del usuario autenticado
    return {"message": "Menú actualizado exitosamente"}


@router.get("/date/{date}", status_code=200)
async def get_menu_by_date(date: date, current_user=Depends(get_current_user), handler=Depends(get_menu_by_date_handler)):
    menu = await handler.handle(GetMenuByDateQuery(user_id=current_user.id, week_start=date))
    return menu
