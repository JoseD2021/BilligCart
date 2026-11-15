from __future__ import annotations

import asyncio

from fastapi import WebSocket


class WebSocketSink:
    """Adapta un WebSocket de FastAPI al puerto MessageSink.

    Igualdad por identidad (necesaria para los sets del registro) y un lock
    para que dos corutinas no escriban a la vez en el mismo socket.
    """

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket
        self._lock = asyncio.Lock()

    async def send(self, message: dict) -> None:
        async with self._lock:
            await self._ws.send_json(message)
