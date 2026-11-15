from __future__ import annotations

from dataclasses import dataclass

from .entities import Location


@dataclass(frozen=True, slots=True)
class PersistenceThrottle:
    """Decide cuándo una ubicación se envía a RabbitMQ (throttling temporal).

    Publica si pasaron >= min_interval_s Y (el repartidor se movió >= min_distance_m
    O pasaron >= heartbeat_s, para registrar que sigue vivo aunque esté quieto).
    """

    min_interval_s: float = 10.0
    min_distance_m: float = 15.0
    heartbeat_s: float = 60.0

    def should_publish(self, last_published: Location | None, current: Location) -> bool:
        if last_published is None:
            return True
        elapsed = current.ts - last_published.ts
        if elapsed < self.min_interval_s:
            return False
        moved = current.distance_m(last_published)
        return moved >= self.min_distance_m or elapsed >= self.heartbeat_s
