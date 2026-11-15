from __future__ import annotations

import math
from dataclasses import dataclass

from .errors import InvalidLocation


@dataclass(frozen=True, slots=True)
class Location:
    lat: float
    lng: float
    ts: float  # epoch en segundos, asignado por el servidor
    accuracy: float | None = None
    heading: float | None = None
    speed: float | None = None

    def __post_init__(self) -> None:
        if not (math.isfinite(self.lat) and -90 <= self.lat <= 90):
            raise InvalidLocation("lat fuera de rango")
        if not (math.isfinite(self.lng) and -180 <= self.lng <= 180):
            raise InvalidLocation("lng fuera de rango")

    def distance_m(self, other: Location) -> float:
        """Distancia haversine en metros."""
        r = 6_371_000
        p1, p2 = math.radians(self.lat), math.radians(other.lat)
        dphi = p2 - p1
        dlmb = math.radians(other.lng - self.lng)
        a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
        return 2 * r * math.asin(math.sqrt(a))
