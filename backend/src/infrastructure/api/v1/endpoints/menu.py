from fastapi import APIRouter, Depends
from datetime import date

from src.application.commands.menu.create_menu import CreateMenuCommand
from src.application.queries.menu.get_current_menu import GetCurrentMenuQuery
from src.application.queries.menu.get_menu_by_date import GetMenuByDateQuery
from src.infrastructure.api.v1.dependencies import get_current_user, get_create_menu_handler, get_current_menu_handler, get_menu_by_date_handler
from src.infrastructure.api.v1.dependencies import get_weekly_menu, get_generate_weekly_menu

router = APIRouter(prefix="/menu", tags=["Menu"])

@router.get("/current", status_code=200)
async def get_current(current_user=Depends(get_current_user), handler=Depends(get_current_menu_handler)):
    # Lógica para obtener el menú actual del usuario autenticado
    menu = await handler.handle(GetCurrentMenuQuery(user_id=current_user.id))
    return menu

@router.get("/weekly")
async def weekly(current_user=Depends(get_current_user), handler=Depends(get_weekly_menu)):
    return await handler.execute(current_user.id)


@router.post("/generate", status_code=201)
async def generate(current_user=Depends(get_current_user), handler=Depends(get_generate_weekly_menu)):
    return await handler.execute(current_user.id)


@router.post("/create", status_code=201)
async def create(current_user=Depends(get_current_user), handler=Depends(get_create_menu_handler)):
    menu = await handler.handle(CreateMenuCommand(user_id=current_user.id))
    return menu

@router.get("/date/{date}", status_code=200)
async def get_by_date(date: date, current_user=Depends(get_current_user), handler=Depends(get_menu_by_date_handler)):
    menu = await handler.handle(GetMenuByDateQuery(user_id=current_user.id, week_start=date))
    return menu
