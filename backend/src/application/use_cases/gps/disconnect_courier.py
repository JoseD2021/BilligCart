from __future__ import annotations

from dataclasses import dataclass

from src.application.gps import messages
from src.application.gps.broadcast import broadcast
from src.application.gps.ports import LocationStore, MessageSink, TrackingRegistry
from src.application.gps.publishing import BackgroundPublisher
from src.events.contracts.gps_events import LocationRecorded


@dataclass(frozen=True)
class DisconnectCourierCommand:
    user_id: str
    order_id: str
    sink: MessageSink


class DisconnectCourierHandler:
    """El repartidor se desconecta: se guarda su última posición conocida."""

    def __init__(
        self,
        registry: TrackingRegistry,
        store: LocationStore,
        publisher: BackgroundPublisher,
    ) -> None:
        self._registry = registry
        self._store = store
        self._publisher = publisher

    async def handle(self, cmd: DisconnectCourierCommand) -> None:
        if not await self._registry.clear_courier(cmd.order_id, cmd.sink):
            return  # una sesión más nueva del repartidor ya ocupó su lugar

        last = await self._store.latest(cmd.order_id)
        published = await self._store.last_published(cmd.order_id)
        if last is not None and (published is None or published.ts < last.ts):
            await self._store.mark_published(cmd.order_id, last)
            self._publisher.submit(
                LocationRecorded.from_location(
                    cmd.order_id, cmd.user_id, last, reason="courier_disconnected"
                )
            )
        await broadcast(self._registry, cmd.order_id, messages.courier_status(False))
