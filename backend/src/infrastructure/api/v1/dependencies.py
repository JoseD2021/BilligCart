from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from  application.interfaces.auth_service import AuthService
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