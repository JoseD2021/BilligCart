from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from application.interfaces.auth_service import AuthService
from application.commands.login_user import LoginUserHandler
from application.commands.register_user import RegisterUserHandler
from application.commands.create_menu import CreateMenuHandler
from application.queries.get_current_menu import GetCurrentMenuHandler
from application.queries.get_menu_by_date import GetMenuByDateHandler
from application.commands.create_plato import CreatePlatoHandler
from application.commands.update_plato import UpdatePlatoHandler
from application.queries.get_plato_by_day import GetPlatoByDayHandler
from application.commands.delete_plato import DeletePlatoHandler
from infrastructure.supabase.repositories.plato_repository import SupabasePlatoRepository
from domain.repositories.plato_repository import PlatoRepository
from domain.repositories.menu_repository import MenuRepository
from infrastructure.supabase.repositories.menu_repository import SupabaseMenuRepository
from domain.repositories.preferencias_repository import PreferenciasRepository
from infrastructure.supabase.repositories.preferencias_repository import SupabasePreferenciasRepository
from infrastructure.supabase.auth_service import SupabaseAuthService
from domain.errors import InvalidCredentials
from domain.entities.user import User

bearer = HTTPBearer()

# ------- Auth / User -------------

def get_auth_service(request: Request) -> AuthService:
    return SupabaseAuthService(request.app.state.supabase)

async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    auth: AuthService = Depends(get_auth_service),
) -> User:
    try:
        return await auth.get_user_from_token(creds.credentials)
    except InvalidCredentials:
        raise HTTPException(401, "Token inválido")
    
def get_preferencias_repository(
    request: Request
) -> PreferenciasRepository:
    return SupabasePreferenciasRepository(request.app.state.supabase)

def get_register_handler(
    auth: AuthService = Depends(get_auth_service),
    preferencias: PreferenciasRepository = Depends(get_preferencias_repository),
) -> RegisterUserHandler:
    return RegisterUserHandler(auth, preferencias)

def get_login_handler(
    auth: AuthService = Depends(get_auth_service),
) -> LoginUserHandler:
    return LoginUserHandler(auth)

# -------- Menu ------------
def get_menu_repository(
    request: Request
) -> MenuRepository:
    return SupabaseMenuRepository(request.app.state.supabase)

def get_create_menu_handler(
    menu: MenuRepository = Depends(get_menu_repository),
) -> CreateMenuHandler:
    return CreateMenuHandler(menu)

def get_current_menu_handler(
    menu: MenuRepository = Depends(get_menu_repository),
) -> GetCurrentMenuHandler:
    return GetCurrentMenuHandler(menu)

def get_menu_by_date_handler(
    menu: MenuRepository = Depends(get_menu_repository),
) -> GetMenuByDateHandler:
    return GetMenuByDateHandler(menu)

# -------- Platos ---------
def get_plato_repository(
    request: Request
) -> PlatoRepository:
    return SupabasePlatoRepository(request.app.state.supabase)

def get_create_plato_handler(
    plato: PlatoRepository = Depends(get_plato_repository),
) -> CreatePlatoHandler:
    return CreatePlatoHandler(plato)

def get_update_plato_handler(
    plato: PlatoRepository = Depends(get_plato_repository),
) -> UpdatePlatoHandler:
    return UpdatePlatoHandler(plato)

def get_plato_by_day_handler(
    plato: PlatoRepository = Depends(get_plato_repository),
) -> GetPlatoByDayHandler:
    return GetPlatoByDayHandler(plato)

def get_delete_plato_handler(
    plato: PlatoRepository = Depends(get_plato_repository),
) -> DeletePlatoHandler:
    return DeletePlatoHandler(plato)