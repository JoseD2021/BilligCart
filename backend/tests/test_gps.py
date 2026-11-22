import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.application.gps.broadcast import broadcast
from src.application.gps.errors import Forbidden
from src.application.gps.publishing import BackgroundPublisher
from src.application.use_cases.gps.connect_courier import ConnectCourierCommand, ConnectCourierHandler
from src.application.use_cases.gps.disconnect_courier import DisconnectCourierCommand, DisconnectCourierHandler
from src.application.use_cases.gps.receive_courier_location import ReceiveCourierLocationCommand, ReceiveCourierLocationHandler
from src.application.use_cases.gps.subscribe_to_tracking import SubscribeToTrackingCommand, SubscribeToTrackingHandler
from src.application.use_cases.gps.unsubscribe_from_tracking import UnsubscribeFromTrackingCommand, UnsubscribeFromTrackingHandler
from src.domain.entities.gps.entities import Location
from src.domain.entities.gps.policies import PersistenceThrottle
from src.domain.entities.user import User
from src.domain.errors import AccessDenied
from src.events.contracts.gps_events import LocationRecorded
from src.infrastructure.gps.security.supabase_order_access import SupabaseOrderAccess
from src.infrastructure.gps.web.routes import require_courier_role
from src.infrastructure.gps.state.in_memory import InMemoryLocationStore, InMemoryTrackingRegistry


class Sink:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = []

    async def send(self, message):
        if self.fail:
            raise RuntimeError("closed")
        self.messages.append(message)


class Clock:
    def __init__(self, now=1000.0):
        self._now = now

    def now(self):
        return self._now


class GpsTests(unittest.IsolatedAsyncioTestCase):
    def test_courier_stream_requires_repartidor_role(self):
        with self.assertRaises(AccessDenied):
            require_courier_role(User("u1", "user@example.com", "user"))
        require_courier_role(User("u1", "courier@example.com", "repartidor"))

    async def test_subscribe_sends_last_location_and_requests_live_mode(self):
        registry = InMemoryTrackingRegistry()
        store = InMemoryLocationStore()
        await store.save_latest("1", Location(1.0, 2.0, 10.0))
        courier = Sink()
        await registry.set_courier("1", courier)
        access = SimpleNamespace(is_customer=AsyncMock(return_value=True))
        client = Sink()
        await SubscribeToTrackingHandler(access, registry, store, 3000).handle(
            SubscribeToTrackingCommand("u1", "1", client)
        )
        self.assertEqual(client.messages[0]["type"], "courier_status")
        self.assertEqual(client.messages[1]["type"], "location")
        self.assertEqual(courier.messages[0], {"type": "start_streaming", "interval_ms": 3000, "mode": "live"})

    async def test_unsubscribe_last_client_switches_courier_to_idle(self):
        registry = InMemoryTrackingRegistry()
        courier = Sink()
        client = Sink()
        await registry.set_courier("1", courier)
        await registry.add_subscriber("1", client)
        await UnsubscribeFromTrackingHandler(registry, 10000).handle(UnsubscribeFromTrackingCommand("1", client))
        self.assertEqual(courier.messages[0]["mode"], "idle")

    async def test_connect_courier_requires_assignment_and_uses_idle_without_subscribers(self):
        registry = InMemoryTrackingRegistry()
        sink = Sink()
        access = SimpleNamespace(is_courier=AsyncMock(return_value=False))
        with self.assertRaises(Forbidden):
            await ConnectCourierHandler(access, registry, 3000, 10000).handle(ConnectCourierCommand("c1", "1", sink))
        access.is_courier.return_value = True
        await ConnectCourierHandler(access, registry, 3000, 10000).handle(ConnectCourierCommand("c1", "1", sink))
        self.assertEqual(sink.messages[0]["mode"], "idle")

    async def test_receive_location_broadcasts_and_publishes_on_throttle(self):
        registry = InMemoryTrackingRegistry()
        store = InMemoryLocationStore()
        client = Sink()
        await registry.add_subscriber("1", client)
        published = []
        publisher = BackgroundPublisher(SimpleNamespace(publish=AsyncMock(side_effect=lambda e: published.append(e))))
        handler = ReceiveCourierLocationHandler(registry, store, publisher, PersistenceThrottle(10, 15, 60), Clock(100.0))
        await handler.handle(ReceiveCourierLocationCommand("c1", "1", {"lat": 1.0, "lng": 2.0}))
        self.assertEqual(client.messages[0]["type"], "location")
        await publisher.drain()
        self.assertEqual(len(published), 1)
        self.assertIsInstance(published[0], LocationRecorded)

    async def test_disconnect_publishes_last_unpublished_location(self):
        registry = InMemoryTrackingRegistry()
        store = InMemoryLocationStore()
        sink = Sink()
        await registry.set_courier("1", sink)
        await store.save_latest("1", Location(1, 2, 50))
        published = []
        publisher = BackgroundPublisher(SimpleNamespace(publish=AsyncMock(side_effect=lambda e: published.append(e))))
        await DisconnectCourierHandler(registry, store, publisher).handle(DisconnectCourierCommand("c1", "1", sink))
        await publisher.drain()
        self.assertEqual(published[0].reason, "courier_disconnected")

    async def test_broadcast_removes_dead_subscriber(self):
        registry = InMemoryTrackingRegistry()
        dead = Sink(fail=True)
        ok = Sink()
        await registry.add_subscriber("1", dead)
        await registry.add_subscriber("1", ok)
        await broadcast(registry, "1", {"type": "location"})
        self.assertEqual(ok.messages[0]["type"], "location")
        self.assertEqual(await registry.get_subscribers("1"), [ok])

    async def test_supabase_access_allows_pending_unassigned_courier_and_assigns(self):
        row = {"user_id": "u1", "repartidor_id": None, "estado": "pendiente"}
        updated = {"user_id": "u1", "repartidor_id": "c1", "estado": "confirmado"}

        class Query:
            def __init__(self, data):
                self.data = data
            def select(self, *a, **k): return self
            def eq(self, *a, **k): return self
            def limit(self, *a, **k): return self
            def update(self, *a, **k): return self
            def is_(self, *a, **k): return self
            def in_(self, *a, **k): return self
            async def execute(self): return SimpleNamespace(data=[self.data] if self.data else [])

        class Client:
            def __init__(self):
                self.calls = 0
            def table(self, name):
                self.calls += 1
                if self.calls in (1, 3):
                    return Query(row if self.calls == 1 else updated)
                return Query(updated)

        access = SupabaseOrderAccess(Client())
        self.assertTrue(await access.is_courier("c1", "1"))