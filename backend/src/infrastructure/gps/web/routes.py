from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.application.gps.errors import Forbidden
from src.application.interfaces.auth_service import AuthService
from src.application.use_cases.gps.connect_courier import ConnectCourierCommand
from src.application.use_cases.gps.disconnect_courier import DisconnectCourierCommand
from src.application.use_cases.gps.receive_courier_location import ReceiveCourierLocationCommand
from src.application.use_cases.gps.subscribe_to_tracking import SubscribeToTrackingCommand
from src.application.use_cases.gps.unsubscribe_from_tracking import UnsubscribeFromTrackingCommand
from src.domain.entities.gps.errors import InvalidLocation
from src.domain.entities.user import User
from src.domain.errors import InvalidCredentials
from src.infrastructure.gps.web.websocket_sink import WebSocketSink

if TYPE_CHECKING:
    from src.infrastructure.gps.bootstrap import GpsContainer

router = APIRouter()

ORDER_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
AUTH_TIMEOUT_S = 5
CLOSE_BAD_REQUEST, CLOSE_UNAUTHORIZED, CLOSE_FORBIDDEN = 4400, 4401, 4403


def _gps(ws: WebSocket) -> GpsContainer:
    # Mismo patrón que `request.app.state.supabase` en dependencies.py
    # (Depends con `Request` no funciona en WebSockets).
    return ws.app.state.gps


async def _authenticate(ws: WebSocket, auth: AuthService) -> User:
    """El token viaja en el primer mensaje (no en la URL, para que no quede en logs)."""
    await ws.accept()
    try:
        raw = await asyncio.wait_for(ws.receive_text(), AUTH_TIMEOUT_S)
        msg = json.loads(raw)
    except (asyncio.TimeoutError, ValueError) as exc:
        raise InvalidCredentials("auth timeout o mensaje inválido") from exc
    if not isinstance(msg, dict) or msg.get("type") != "auth" or not isinstance(msg.get("token"), str):
        raise InvalidCredentials("se esperaba {type:'auth', token}")
    return await auth.get_user_from_token(msg["token"])


async def _messages(ws: WebSocket) -> AsyncIterator[dict]:
    while True:
        text = await ws.receive_text()
        try:
            msg = json.loads(text)
        except ValueError:
            continue
        if isinstance(msg, dict):
            yield msg


async def _close(ws: WebSocket, exc: Exception) -> None:
    code = CLOSE_UNAUTHORIZED if isinstance(exc, InvalidCredentials) else CLOSE_FORBIDDEN
    try:
        await ws.close(code=code)
    except RuntimeError:
        pass


@router.websocket("/ws/tracking/{order_id}")
async def customer_tracking(ws: WebSocket, order_id: str) -> None:
    """Cliente (mapa). Recibe courier_status y location."""
    if not ORDER_ID.match(order_id):
        await ws.close(code=CLOSE_BAD_REQUEST)
        return
    c = _gps(ws)
    sink = WebSocketSink(ws)
    user: User | None = None
    try:
        user = await _authenticate(ws, c.auth)
        await c.subscribe.handle(SubscribeToTrackingCommand(str(user.id), order_id, sink))
        async for msg in _messages(ws):
            if msg.get("type") == "ping":
                await sink.send({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except (InvalidCredentials, Forbidden) as exc:
        await _close(ws, exc)
    finally:
        if user is not None:  # idempotente aunque subscribe haya fallado a medias
            await c.unsubscribe.handle(UnsubscribeFromTrackingCommand(order_id, sink))


@router.websocket("/ws/courier/{order_id}")
async def courier_stream(ws: WebSocket, order_id: str) -> None:
    """Repartidor. Recibe start/stop_streaming y envía location."""
    if not ORDER_ID.match(order_id):
        await ws.close(code=CLOSE_BAD_REQUEST)
        return
    c = _gps(ws)
    sink = WebSocketSink(ws)
    user: User | None = None
    try:
        user = await _authenticate(ws, c.auth)
        await c.connect_courier.handle(ConnectCourierCommand(str(user.id), order_id, sink))
        async for msg in _messages(ws):
            kind = msg.get("type")
            if kind == "location":
                try:
                    await c.receive_location.handle(
                        ReceiveCourierLocationCommand(str(user.id), order_id, msg)
                    )
                except InvalidLocation:
                    await sink.send({"type": "error", "code": "invalid_location"})
            elif kind == "ping":
                await sink.send({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except (InvalidCredentials, Forbidden) as exc:
        await _close(ws, exc)
    finally:
        if user is not None:
            await c.disconnect_courier.handle(
                DisconnectCourierCommand(str(user.id), order_id, sink)
            )
