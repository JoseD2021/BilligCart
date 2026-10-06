from dataclasses import dataclass

from  application.interfaces.auth_service import AuthService
from domain.entities.user import User

@dataclass(frozen=True)
class RegisterUserCommand:
    email: str
    password: str

class RegisterUserHandler:
    def __init__(self, auth: AuthService):
        self._auth = auth

    async def handle(self, cmd: RegisterUserCommand) -> User:
        user = await self._auth.sign_up(cmd.email, cmd.password)
        # TODO: await self._events.publish(UserRegistered(user.id, user.email))
        return user