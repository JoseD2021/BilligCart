from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from application.interfaces.auth_service import AuthService
from application.commands.auth.login_user import LoginUserHandler
from application.commands.auth.register_user import RegisterUserHandler
from application.commands.menu.create_menu import CreateMenuHandler
from application.queries.menu.get_current_menu import GetCurrentMenuHandler
from application.queries.menu.get_menu_by_date import GetMenuByDateHandler
from application.commands.plato.create_plato import CreatePlatoHandler
from application.commands.plato.update_plato import UpdatePlatoHandler
from application.queries.plato.get_plato_by_day import GetPlatoByDayHandler
from application.commands.plato.delete_plato import DeletePlatoHandler
from application.commands.ingrediente.create_ingrediente import CreateIngredientHandler
from application.commands.ingrediente.delete_ingrediente import DeleteIngredientHandler
from application.commands.ingrediente.update_ingrediente import UpdateIngredientHandler
from application.commands.ingrediente.update_fetch_ingrediente import UpdateFetchIngredientHandler
from application.queries.ingrediente.get_ingrediente import GetIngredientByIdHandler
from application.commands.plato_ingrediente.create_many_plato_ingrediente import CreateManyPlatoIngredienteCommandHandler
from application.commands.plato_ingrediente.update_plato_ingrediente import UpdatePlatoIngredienteCommandHandler
from application.commands.plato_ingrediente.delete_plato_ingrediente import DeletePlatoIngredienteHandler
from application.commands.plato_ingrediente.delete_plato_ingrediente_by_platoid import DeletePlatoIngredienteByPlatoIdHandler
from application.queries.plato_ingrediente.get_plato_ingrediente_by_platoid import GetPlatoIngredienteByPlatoIdHandler
from application.queries.plato_ingrediente.get_plato_ingrediente_by_id import GetPlatoIngredienteByIdHandler
from domain.repositories.plato_ingrediente_repository import PlatoIngredienteRepository
from infrastructure.supabase.repositories.plato_ingrediente_repository import SupabasePlatoIngredienteRepository
from application.commands.plato_ingrediente.create_plato_ingrediente import CreatePlatoIngredienteCommandHandler
from domain.repositories.ingrediente_repository import IngredienteRepository
from infrastructure.supabase.repositories.plato_repository import SupabasePlatoRepository
from domain.repositories.plato_repository import PlatoRepository
from domain.repositories.menu_repository import MenuRepository
from infrastructure.supabase.repositories.menu_repository import SupabaseMenuRepository
from domain.repositories.preferencias_repository import PreferenciasRepository
from infrastructure.supabase.repositories.preferencias_repository import SupabasePreferenciasRepository
from infrastructure.supabase.repositories.ingrediente_repository import SupabaseIngredienteRepository
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

# -------- Ingredientes ---------
def get_ingrediente_repository(
    request: Request
) -> IngredienteRepository:
    return SupabaseIngredienteRepository(request.app.state.supabase)

def get_create_ingredient_handler(
    ingr: IngredienteRepository = Depends(get_ingrediente_repository),
) -> CreateIngredientHandler:
    return CreateIngredientHandler(ingr)

def get_update_ingredient_handler(
    ingr: IngredienteRepository = Depends(get_ingrediente_repository),
) -> UpdateIngredientHandler:
    return UpdateIngredientHandler(ingr)

def get_update_fetch_ingredient_handler(
    ingr: IngredienteRepository = Depends(get_ingrediente_repository),
) -> UpdateFetchIngredientHandler:
    return UpdateFetchIngredientHandler(ingr)

def get_delete_ingredient_handler(
    ingr: IngredienteRepository = Depends(get_ingrediente_repository),
) -> DeleteIngredientHandler:
    return DeleteIngredientHandler(ingr)

def get_get_ingredient_by_id_handler(
    ingr: IngredienteRepository = Depends(get_ingrediente_repository),
) -> GetIngredientByIdHandler:
    return GetIngredientByIdHandler(ingr)

# -------- PlatoIngrediente ---------
def get_plato_ingrediente_repository(
    request: Request
) -> PlatoIngredienteRepository:
    return SupabasePlatoIngredienteRepository(request.app.state.supabase)

def get_create_plato_ingrediente_handler(
    pltingr: PlatoIngredienteRepository = Depends(get_plato_ingrediente_repository),
) -> CreatePlatoIngredienteCommandHandler:
    return CreatePlatoIngredienteCommandHandler(pltingr)

def get_create_many_plato_ingrediente_handler(
    pltingr: PlatoIngredienteRepository = Depends(get_plato_ingrediente_repository),
) -> CreateManyPlatoIngredienteCommandHandler:
    return CreateManyPlatoIngredienteCommandHandler(pltingr)

def get_update_plato_ingrediente_handler(
    pltingr: PlatoIngredienteRepository = Depends(get_plato_ingrediente_repository),
) -> UpdatePlatoIngredienteCommandHandler:
    return UpdatePlatoIngredienteCommandHandler(pltingr)

def get_delete_plato_ingrediente_handler(
    pltingr: PlatoIngredienteRepository = Depends(get_plato_ingrediente_repository),
) -> "DeletePlatoIngredienteHandler":
    return DeletePlatoIngredienteHandler(pltingr)

def get_delete_plato_ingrediente_by_plato_id_handler(
    pltingr: PlatoIngredienteRepository = Depends(get_plato_ingrediente_repository),
) -> "DeletePlatoIngredienteByPlatoIdHandler":
    return DeletePlatoIngredienteByPlatoIdHandler(pltingr)

def get_get_plato_ingrediente_by_id_handler(
    pltingr: PlatoIngredienteRepository = Depends(get_plato_ingrediente_repository),
) -> "GetPlatoIngredienteByIdHandler":
    return GetPlatoIngredienteByIdHandler(pltingr)

def get_get_plato_ingrediente_by_plato_id_handler(
    pltingr: PlatoIngredienteRepository = Depends(get_plato_ingrediente_repository),
) -> "GetPlatoIngredienteByPlatoIdHandler":
    return GetPlatoIngredienteByPlatoIdHandler(pltingr)