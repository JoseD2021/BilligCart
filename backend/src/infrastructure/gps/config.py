from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GpsSettings:
    """Solo lo propio del GPS. Supabase y RabbitMQ se configuran donde ya lo haces."""

    stream_interval_ms: int = 3000
    throttle_interval_s: float = 10.0
    throttle_distance_m: float = 15.0
    throttle_heartbeat_s: float = 60.0

    @classmethod
    def from_env(cls) -> GpsSettings:
        env = os.environ
        return cls(
            stream_interval_ms=int(env.get("GPS_STREAM_INTERVAL_MS", 3000)),
            throttle_interval_s=float(env.get("GPS_THROTTLE_INTERVAL_S", 10)),
            throttle_distance_m=float(env.get("GPS_THROTTLE_DISTANCE_M", 15)),
            throttle_heartbeat_s=float(env.get("GPS_THROTTLE_HEARTBEAT_S", 60)),
        )
