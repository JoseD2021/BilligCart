"""Composición del GPS: arma handlers y estado. Equivale al `dependencies.py` de la API."""
from __future__ import annotations

from dataclasses import dataclass

from src.application.gps.ports import Clock, OrderAccessPolicy
from src.application.gps.publishing import BackgroundPublisher
from src.application.interfaces.auth_service import AuthService
from src.application.use_cases.gps.connect_courier import ConnectCourierHandler
from src.application.use_cases.gps.disconnect_courier import DisconnectCourierHandler
from src.application.use_cases.gps.receive_courier_location import ReceiveCourierLocationHandler
from src.application.use_cases.gps.subscribe_to_tracking import SubscribeToTrackingHandler
from src.application.use_cases.gps.unsubscribe_from_tracking import UnsubscribeFromTrackingHandler
from src.domain.entities.gps.policies import PersistenceThrottle
from src.events.application.event_publisher import EventPublisher
from src.infrastructure.gps.config import GpsSettings
from src.infrastructure.gps.state.in_memory import (
    InMemoryLocationStore,
    InMemoryTrackingRegistry,
    SystemClock,
)


@dataclass(frozen=True)
class GpsContainer:
    auth: AuthService
    subscribe: SubscribeToTrackingHandler
    unsubscribe: UnsubscribeFromTrackingHandler
    connect_courier: ConnectCourierHandler
    disconnect_courier: DisconnectCourierHandler
    receive_location: ReceiveCourierLocationHandler
    background: BackgroundPublisher


def build_gps_container(
    *,
    auth: AuthService,
    access: OrderAccessPolicy,
    events: EventPublisher,
    settings: GpsSettings,
    clock: Clock | None = None,
) -> GpsContainer:
    # El registro y el almacén se crean UNA vez: todas las conexiones deben compartirlos.
    registry = InMemoryTrackingRegistry()
    store = InMemoryLocationStore()
    background = BackgroundPublisher(events)
    throttle = PersistenceThrottle(
        settings.throttle_interval_s,
        settings.throttle_distance_m,
        settings.throttle_heartbeat_s,
    )
    interval = settings.stream_interval_ms

    return GpsContainer(
        auth=auth,
        subscribe=SubscribeToTrackingHandler(access, registry, store, interval),
        unsubscribe=UnsubscribeFromTrackingHandler(registry),
        connect_courier=ConnectCourierHandler(access, registry, interval),
        disconnect_courier=DisconnectCourierHandler(registry, store, background),
        receive_location=ReceiveCourierLocationHandler(
            registry, store, background, throttle, clock or SystemClock()
        ),
        background=background,
    )
