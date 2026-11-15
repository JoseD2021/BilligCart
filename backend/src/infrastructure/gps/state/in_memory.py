from __future__ import annotations

import time
from collections import defaultdict

from src.application.gps.ports import MessageSink
from src.domain.entities.gps.entities import Location


class InMemoryTrackingRegistry:
    """Implementa TrackingRegistry. Válido para UNA instancia del servicio.

    Todo ocurre en un solo event loop y sin `await` internos, así que no necesita locks.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, set[MessageSink]] = defaultdict(set)
        self._couriers: dict[str, MessageSink] = {}

    async def add_subscriber(self, order_id: str, sink: MessageSink) -> int:
        self._subscribers[order_id].add(sink)
        return len(self._subscribers[order_id])

    async def remove_subscriber(self, order_id: str, sink: MessageSink) -> int:
        subs = self._subscribers.get(order_id)
        if subs is None:
            return 0
        subs.discard(sink)
        if not subs:
            del self._subscribers[order_id]
            return 0
        return len(subs)

    async def get_subscribers(self, order_id: str) -> list[MessageSink]:
        return list(self._subscribers.get(order_id, ()))

    async def set_courier(self, order_id: str, sink: MessageSink) -> None:
        self._couriers[order_id] = sink

    async def clear_courier(self, order_id: str, sink: MessageSink) -> bool:
        if self._couriers.get(order_id) is sink:
            del self._couriers[order_id]
            return True
        return False

    async def get_courier(self, order_id: str) -> MessageSink | None:
        return self._couriers.get(order_id)


class InMemoryLocationStore:
    """Implementa LocationStore. Pendiente: purgar pedidos finalizados (TTL)."""

    def __init__(self) -> None:
        self._latest: dict[str, Location] = {}
        self._published: dict[str, Location] = {}

    async def latest(self, order_id: str) -> Location | None:
        return self._latest.get(order_id)

    async def save_latest(self, order_id: str, location: Location) -> None:
        self._latest[order_id] = location

    async def last_published(self, order_id: str) -> Location | None:
        return self._published.get(order_id)

    async def mark_published(self, order_id: str, location: Location) -> None:
        self._published[order_id] = location


class SystemClock:
    def now(self) -> float:
        return time.time()
