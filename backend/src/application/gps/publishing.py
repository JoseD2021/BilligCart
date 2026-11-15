from __future__ import annotations

import asyncio
import logging

from src.events.application.event_publisher import EventPublisher
from src.events.contracts.base_event import BaseEvent

log = logging.getLogger(__name__)


class BackgroundPublisher:
    """Publica con tu EventPublisher sin bloquear el camino en vivo (hot path).

    Si RabbitMQ está lento o caído, el mapa del cliente sigue funcionando.
    """

    def __init__(self, publisher: EventPublisher) -> None:
        self._publisher = publisher
        self._tasks: set[asyncio.Task] = set()

    def submit(self, event: BaseEvent) -> None:
        task = asyncio.create_task(self._run(event))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, event: BaseEvent) -> None:
        try:
            await self._publisher.publish(event)
        except Exception:
            log.exception("No se pudo publicar el evento %s", event.event_type)

    async def drain(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
