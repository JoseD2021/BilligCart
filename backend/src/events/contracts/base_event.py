from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar
from uuid import uuid4


@dataclass(frozen=True, kw_only=True)
class BaseEvent:
    """
    Contrato común para todos los eventos de la aplicación.

    Cada evento tiene un identificador único y la fecha
    en la que ocurrió.
    """

    event_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    EVENT_TYPE: ClassVar[str] = ""

    @classmethod
    def get_event_type(cls) -> str:
        """
        Devuelve el nombre estable del evento usado
        como routing key en RabbitMQ.
        """
        if cls.EVENT_TYPE:
            return cls.EVENT_TYPE

        return f"{cls.__module__}.{cls.__qualname__}"

    @property
    def event_type(self) -> str:
        return self.get_event_type()

    def to_payload(self) -> dict[str, Any]:
        """
        Obtiene únicamente los datos propios del evento,
        excluyendo sus metadatos comunes.
        """
        data = asdict(self)
        data.pop("event_id", None)
        data.pop("occurred_at", None)
        return data

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        event_id: str,
        occurred_at: str,
    ) -> "BaseEvent":
        """
        Reconstruye un evento a partir del mensaje recibido.
        Los eventos con campos complejos pueden sobrescribir
        este método para controlar su deserialización.
        """
        timestamp = datetime.fromisoformat(
            occurred_at.replace("Z", "+00:00")
        )

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        return cls(
            **payload,
            event_id=event_id,
            occurred_at=timestamp,
        )