from dataclasses import dataclass
from typing import ClassVar

from src.events.contracts.base_event import BaseEvent


@dataclass(frozen=True, kw_only=True)
class MenuGenerationStarted(BaseEvent):
    EVENT_TYPE: ClassVar[str] = "ai.menu_generation.started.v1"

    request_id: str
    model: str


@dataclass(frozen=True, kw_only=True)
class MenuGenerationCompleted(BaseEvent):
    EVENT_TYPE: ClassVar[str] = "ai.menu_generation.completed.v1"

    request_id: str
    model: str
    duration_ms: int

    # Datos necesarios para que quien consuma el evento guarde el menú:
    # el dueño del menú y la respuesta cruda que devolvió la IA.
    user_id: str | None = None
    response: str | None = None


@dataclass(frozen=True, kw_only=True)
class MenuGenerationFailed(BaseEvent):
    EVENT_TYPE: ClassVar[str] = "ai.menu_generation.failed.v1"

    request_id: str
    model: str
    error_type: str