"""Protocolo de mensajes WebSocket (servidor -> clientes)."""
from __future__ import annotations

from src.domain.entities.gps.entities import Location

STOP_STREAMING: dict = {"type": "stop_streaming"}


def start_streaming(interval_ms: int, mode: str = "live") -> dict:
    return {"type": "start_streaming", "interval_ms": interval_ms, "mode": mode}


def courier_status(online: bool) -> dict:
    return {"type": "courier_status", "online": online}


def location(order_id: str, loc: Location) -> dict:
    return {
        "type": "location",
        "order_id": order_id,
        "lat": loc.lat,
        "lng": loc.lng,
        "ts": loc.ts,
        "accuracy": loc.accuracy,
        "heading": loc.heading,
        "speed": loc.speed,
    }
