from dataclasses import dataclass

from src.application.interfaces.auth_service import AuthService
from src.domain.entities.preferencias import Preferencias
from src.domain.entities.user import User
from src.domain.repositories.preferencias_repository import PreferenciasRepository

@dataclass(frozen=True)
class RegisterUserCommand:
    email: str
    password: str

class RegisterUserHandler:
    def __init__(self, auth: AuthService, preferencias: PreferenciasRepository):
        self._auth = auth
        self._preferencias = preferencias

    async def handle(self, cmd: RegisterUserCommand) -> User:
        user = await self._auth.sign_up(cmd.email, cmd.password)
        
        # TODO: await self._events.publish(UserRegistered(user.id, user.email))
        # Las preferencias se deberían crear despues del evento ^ en un handler del evento
        await self._preferencias.save(Preferencias.default(user.id))
        return user