from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
    REPARTIDOR = "repartidor"

    @classmethod
    def from_value(cls, value: object) -> "UserRole":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            for role in cls:
                if role.value == normalized:
                    return role
        return cls.USER