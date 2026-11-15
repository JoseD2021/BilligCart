from __future__ import annotations

from dataclasses import dataclass

from src.application.gps import messages
from src.application.gps.broadcast import safe_send
from src.application.gps.ports import MessageSink, TrackingRegistry


@dataclass(frozen=True)
class UnsubscribeFromTrackingCommand:
    order_id: str
    sink: MessageSink


class UnsubscribeFromTrackingHandler:
    """El cliente sale del mapa: si era el último, el repartidor deja de transmitir."""

    def __init__(self, registry: TrackingRegistry) -> None:
        self._registry = registry

    async def handle(self, cmd: UnsubscribeFromTrackingCommand) -> None:
        remaining = await self._registry.remove_subscriber(cmd.order_id, cmd.sink)
        if remaining == 0:
            courier = await self._registry.get_courier(cmd.order_id)
            if courier is not None:
                await safe_send(courier, messages.STOP_STREAMING)
