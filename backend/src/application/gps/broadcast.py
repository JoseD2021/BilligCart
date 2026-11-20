from __future__ import annotations

import asyncio
import logging

from .ports import MessageSink, TrackingRegistry

log = logging.getLogger(__name__)


async def safe_send(sink: MessageSink, message: dict) -> bool:
    try:
        await sink.send(message)
        return True
    except Exception:  # conexión muerta: no debe tumbar al resto
        log.debug("send failed", exc_info=True)
        return False


async def broadcast(registry: TrackingRegistry, order_id: str, message: dict) -> None:
    """Envía a todos los suscriptores del pedido y retira los que fallan."""
    sinks = await registry.get_subscribers(order_id)
    results = await asyncio.gather(*(safe_send(s, message) for s in sinks))
    for sink, ok in zip(sinks, results):
        if not ok:
            await registry.remove_subscriber(order_id, sink)
