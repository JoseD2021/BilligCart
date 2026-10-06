from typing import Any

from  application.interfaces.auth_service import AuthService, AuthSession
from domain.entities.user import User
from domain.errors import InvalidCredentials, EmailAlreadyRegistered, InvalidEmail, WeakPassword
from supabase_auth.errors import AuthApiError

class SupabaseAuthService(AuthService):
    def __init__(self, client: Any):
        self._client = client

    async def sign_up(self, email, password) -> User:
        try:
            res = await self._client.auth.sign_up({"email": email, "password": password})
        except AuthApiError as e:
            match e.code:
                case "user_already_exists" | "email_exists":
                    raise EmailAlreadyRegistered(e.message)
                case "email_address_invalid" | "validation_failed":
                    raise InvalidEmail(e.message)
                case "weak_password":
                    raise WeakPassword(e.message)
                case _:
                    raise
        return User(id=res.user.id, email=res.user.email)

    async def sign_in(self, email, password) -> AuthSession:
        try:
            res = await self._client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except AuthApiError as e:
            match e.code:
                case "invalid_credentials":
                    raise InvalidCredentials(e.message)
                case _:
                    raise
        return AuthSession(res.session.access_token, res.session.refresh_token)

    async def get_user_from_token(self, token) -> User:
        try:
            res = await self._client.auth.get_user(token)
        except AuthApiError:
            raise InvalidCredentials("Token inválido o expirado")
        if res is None or res.user is None:
            raise InvalidCredentials("Token inválido o expirado")
        return User(id=res.user.id, email=res.user.email)