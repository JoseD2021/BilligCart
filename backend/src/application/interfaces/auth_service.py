from abc import ABC, abstractmethod
from dataclasses import dataclass
from src.domain.entities.user import User

@dataclass(frozen=True)
class AuthSession:
    access_token: str
    refresh_token: str

class AuthService(ABC):
    @abstractmethod
    async def sign_up(self, email: str, password: str) -> User: ...
    @abstractmethod
    async def sign_in(self, email: str, password: str) -> AuthSession: ...
    @abstractmethod
    async def get_user_from_token(self, access_token: str) -> User: ...