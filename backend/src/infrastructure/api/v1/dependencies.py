from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from  application.interfaces.auth_service import AuthService
from application.commands.login_usuario import LoginUserHandler
from application.commands.register_user import RegisterUserHandler
from domain.repositories.preferencias_repository import PreferenciasRepository
from infrastructure.supabase.repositories.preferencias_repository import SupabasePreferenciasRepository
from infrastructure.supabase.auth_service import SupabaseAuthService
from domain.errors import InvalidCredentials
from domain.entities.user import User

bearer = HTTPBearer()

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