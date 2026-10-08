from dataclasses import dataclass

from domain.enums.plato_tipo import PlatoTipo

@dataclass(frozen=True)
class Plato:
    menu_id: int
    type: PlatoTipo
    name: str
    day: int # 1-7
    
    description: str | None = None
    id: int | None = None  # lo asigna la db
    
    @classmethod
    def default(cls, menu_id: int, type: PlatoTipo, name: str, day: int, description: str | None = None) -> "Plato":
        return cls(menu_id=menu_id, type=type, name=name, day=day, description=description or None)