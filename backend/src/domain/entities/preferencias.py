from dataclasses import dataclass

@dataclass(frozen=True)
class Preferencias:
    user_id: str
    id: int | None = None  # lo asigna la db
    
    @classmethod
    def default(cls, user_id: str) -> "Preferencias":
        return cls(user_id=user_id)