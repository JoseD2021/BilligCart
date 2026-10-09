from dataclasses import dataclass

from  src.application.interfaces.auth_service import AuthService, AuthSession

@dataclass(frozen=True)
class LoginUserCommand:
    email: str
    password: str

class LoginUserHandler:
    def __init__(self, auth: AuthService):
        self._auth = auth

    async def handle(self, cmd: LoginUserCommand) -> AuthSession:
        user = await self._auth.sign_in(cmd.email, cmd.password)
        # TODO: await self._events.publish(UserRegistered(user.id, user.email))
        return user