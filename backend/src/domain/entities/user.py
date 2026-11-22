from __future__ import annotations

from dataclasses import dataclass

from src.domain.enums.role import UserRole


@dataclass(frozen=True)
class User:
    id: str
    email: str
    role: str = UserRole.USER.value

    @property
    def role_enum(self) -> UserRole:
        return UserRole.from_value(self.role)

    @property
    def is_repartidor(self) -> bool:
        return self.role_enum is UserRole.REPARTIDOR
