import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from src.events.contracts.base_event import BaseEvent


def _json_default(value: Any) -> Any:
    """Convierte tipos comunes de Python a valores JSON."""

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Enum):
        return value.value

    if is_dataclass(value):
        return asdict(value)

    raise TypeError(
        f"El tipo {type(value).__name__} no se puede serializar a JSON."
    )


@dataclass(frozen=True)
class EventEnvelope:
    """
    Formato de transporte común para todos los eventos.
    """

    event_id: str
    event_type: str
    occurred_at: str
    payload: dict[str, Any]
    version: int = 1

    @classmethod
    def from_event(cls, event: BaseEvent) -> "EventEnvelope":
        return cls(
            event_id=event.event_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at.isoformat(),
            payload=event.to_payload(),
        )

    def to_json(self) -> str:
        return json.dumps(
            asdict(self),
            default=_json_default,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(
        cls,
        body: bytes | str,
    ) -> "EventEnvelope":
        raw = json.loads(body)

        if not isinstance(raw, dict):
            raise ValueError("El mensaje del evento debe ser un objeto JSON.")

        payload = raw.get("payload")

        if not isinstance(payload, dict):
            raise ValueError("El payload del evento debe ser un objeto JSON.")

        return cls(
            event_id=str(raw["event_id"]),
            event_type=str(raw["event_type"]),
            occurred_at=str(raw["occurred_at"]),
            payload=payload,
            version=int(raw.get("version", 1)),
        )