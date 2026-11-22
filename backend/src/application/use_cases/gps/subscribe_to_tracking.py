from __future__ import annotations

from dataclasses import dataclass

from src.application.gps import messages
from src.application.gps.broadcast import safe_send
from src.application.gps.errors import Forbidden
from src.application.gps.ports import (
    LocationStore,
    MessageSink,
    OrderAccessPolicy,
    TrackingRegistry,
)


@dataclass(frozen=True)
class SubscribeToTrackingCommand:
    user_id: str
    order_id: str
    sink: MessageSink


class SubscribeToTrackingHandler:
    """El cliente abre el mapa: se registra y se le pide al repartidor modo live."""

    def __init__(
        self,
        access: OrderAccessPolicy,
        registry: TrackingRegistry,
        store: LocationStore,
        stream_interval_ms: int,
    ) -> None:
        self._access = access
        self._registry = registry
        self._store = store
        self._interval = stream_interval_ms

    async def handle(self, cmd: SubscribeToTrackingCommand) -> None:
        if not await self._access.is_customer(cmd.user_id, cmd.order_id):
            raise Forbidden("El pedido no pertenece al usuario")

        await self._registry.add_subscriber(cmd.order_id, cmd.sink)
        courier = await self._registry.get_courier(cmd.order_id)

        await cmd.sink.send(messages.courier_status(courier is not None))
        last = await self._store.latest(cmd.order_id)
        if last is not None:
            await cmd.sink.send(messages.location(cmd.order_id, last))
        if courier is not None:
            await safe_send(courier, messages.start_streaming(self._interval, "live"))
