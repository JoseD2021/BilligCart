from __future__ import annotations

from dataclasses import dataclass

from src.application.gps import messages
from src.application.gps.broadcast import broadcast
from src.application.gps.errors import Forbidden
from src.application.gps.ports import MessageSink, OrderAccessPolicy, TrackingRegistry


@dataclass(frozen=True)
class ConnectCourierCommand:
    user_id: str
    order_id: str
    sink: MessageSink


class ConnectCourierHandler:
    """El repartidor se conecta (su app lo hace sola al tener un pedido activo)."""

    def __init__(
        self,
        access: OrderAccessPolicy,
        registry: TrackingRegistry,
        stream_interval_ms: int,
    ) -> None:
        self._access = access
        self._registry = registry
        self._interval = stream_interval_ms

    async def handle(self, cmd: ConnectCourierCommand) -> None:
        if not await self._access.is_courier(cmd.user_id, cmd.order_id):
            raise Forbidden("Pedido no asignado a este repartidor")

        await self._registry.set_courier(cmd.order_id, cmd.sink)
        await broadcast(self._registry, cmd.order_id, messages.courier_status(True))
        # Si ya hay alguien mirando el mapa, empieza a transmitir de inmediato.
        if await self._registry.get_subscribers(cmd.order_id):
            await cmd.sink.send(messages.start_streaming(self._interval))
