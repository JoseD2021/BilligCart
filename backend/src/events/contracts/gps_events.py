from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from src.events.contracts.base_event import BaseEvent

if TYPE_CHECKING:
    from src.domain.entities.gps.entities import Location


@dataclass(frozen=True, kw_only=True)
class LocationRecorded(BaseEvent):
    """Muestra de ubicación del repartidor que debe persistirse.

    Se publica con tu EventPublisher; un worker (a futuro) la guarda en Supabase.
    """

    EVENT_TYPE: ClassVar[str] = "gps.location.recorded"

    order_id: str
    courier_id: str
    lat: float
    lng: float
    ts: float  # epoch en segundos (hora del servidor)
    accuracy: float | None = None
    heading: float | None = None
    speed: float | None = None
    reason: str = "sample"  # "sample" | "courier_disconnected"

    @classmethod
    def from_location(
        cls,
        order_id: str,
        courier_id: str,
        location: Location,
        reason: str = "sample",
    ) -> LocationRecorded:
        return cls(
            order_id=order_id,
            courier_id=courier_id,
            lat=location.lat,
            lng=location.lng,
            ts=location.ts,
            accuracy=location.accuracy,
            heading=location.heading,
            speed=location.speed,
            reason=reason,
        )
