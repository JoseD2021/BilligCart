import inspect
from typing import Any, Callable

from src.events.contracts.base_event import BaseEvent
from src.events.contracts.event_envelope import EventEnvelope


EventHandler = Callable[[BaseEvent], Any]


class EventRegistry:
    """
    Relaciona cada tipo de evento con el handler que lo procesa.

    Se configura una vez al iniciar cada consumidor.
    """

    def __init__(self) -> None:
        self._handlers: dict[
            str,
            tuple[type[BaseEvent], EventHandler],
        ] = {}

    def register(
        self,
        event_class: type[BaseEvent],
        handler: EventHandler,
    ) -> None:
        event_type = event_class.get_event_type()

        if event_type in self._handlers:
            raise ValueError(
                f"Ya existe un handler registrado para {event_type}."
            )

        self._handlers[event_type] = (event_class, handler)

    @property
    def event_types(self) -> tuple[str, ...]:
        return tuple(self._handlers.keys())

    async def dispatch(self, envelope: EventEnvelope) -> None:
        registration = self._handlers.get(envelope.event_type)

        if registration is None:
            raise LookupError(
                f"No existe un handler para {envelope.event_type}."
            )

        event_class, handler = registration

        event = event_class.from_payload(
            envelope.payload,
            event_id=envelope.event_id,
            occurred_at=envelope.occurred_at,
        )

        result = handler(event)

        if inspect.isawaitable(result):
            await result