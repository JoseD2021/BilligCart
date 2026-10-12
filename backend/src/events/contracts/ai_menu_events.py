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


@dataclass(frozen=True, kw_only=True)
class MenuGenerationFailed(BaseEvent):
    EVENT_TYPE: ClassVar[str] = "ai.menu_generation.failed.v1"

    request_id: str
    model: str
    error_type: str