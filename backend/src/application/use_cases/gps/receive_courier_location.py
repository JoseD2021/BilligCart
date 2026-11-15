from __future__ import annotations

from dataclasses import dataclass

from src.application.gps import messages
from src.application.gps.broadcast import broadcast
from src.application.gps.ports import Clock, LocationStore, TrackingRegistry
from src.application.gps.publishing import BackgroundPublisher
from src.domain.entities.gps.entities import Location
from src.domain.entities.gps.errors import InvalidLocation
from src.domain.entities.gps.policies import PersistenceThrottle
from src.events.contracts.gps_events import LocationRecorded


@dataclass(frozen=True)
class ReceiveCourierLocationCommand:
    user_id: str
    order_id: str
    payload: dict


def _opt(value: object) -> float | None:
    return None if value is None else float(value)  # type: ignore[arg-type]


class ReceiveCourierLocationHandler:
    """Camino en vivo: reenvía al instante; solo de vez en cuando publica a RabbitMQ."""

    def __init__(
        self,
        registry: TrackingRegistry,
        store: LocationStore,
        publisher: BackgroundPublisher,
        throttle: PersistenceThrottle,
        clock: Clock,
    ) -> None:
        self._registry = registry
        self._store = store
        self._publisher = publisher
        self._throttle = throttle
        self._clock = clock

    async def handle(self, cmd: ReceiveCourierLocationCommand) -> None:
        p = cmd.payload
        try:
            location = Location(
                lat=float(p["lat"]),
                lng=float(p["lng"]),
                ts=self._clock.now(),  # hora del servidor: evita relojes desfasados
                accuracy=_opt(p.get("accuracy")),
                heading=_opt(p.get("heading")),
                speed=_opt(p.get("speed")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidLocation("payload mal formado") from exc

        await self._store.save_latest(cmd.order_id, location)
        await broadcast(self._registry, cmd.order_id, messages.location(cmd.order_id, location))

        last = await self._store.last_published(cmd.order_id)
        if self._throttle.should_publish(last, location):
            await self._store.mark_published(cmd.order_id, location)
            self._publisher.submit(
                LocationRecorded.from_location(cmd.order_id, cmd.user_id, location)
            )
