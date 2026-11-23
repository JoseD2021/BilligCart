import functools
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.events.application.event_registry import EventRegistry
from src.events.application.payment_event_handlers import (
    on_payment_requested,
    on_payment_succeeded,
)
from src.events.contracts.event_envelope import EventEnvelope
from src.events.contracts.payment_events import PaymentRequested, PaymentSucceeded
from src.events.infrastructure.rabbitmq_event_bus import RabbitMQEventBus


class GeneralPaymentEventTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.projection = SimpleNamespace(apply=AsyncMock())
        self.registry = EventRegistry()
        self.registry.register(PaymentRequested, on_payment_requested)
        self.registry.register(PaymentSucceeded, functools.partial(on_payment_succeeded, projection=self.projection))
        self.bus = RabbitMQEventBus()
        self.bus._forward = AsyncMock()
        self.success = PaymentSucceeded(payment_id="payment", order_id="order", user_id="user",
                                        amount_minor=1000, currency="cop", provider_session_id="cs_test_example")

    def message(self, event):
        return SimpleNamespace(body=EventEnvelope.from_event(event).to_json().encode(), message_id=event.event_id,
                               headers={}, ack=AsyncMock(), nack=AsyncMock())

    async def test_requested_event_is_observed_without_executing_payment_or_projection(self):
        message = self.message(PaymentRequested(payment_id="payment"))
        with self.assertLogs("src.events.application.payment_event_handlers", level="INFO") as logs:
            await self.bus.handle_message(message, self.registry, "application_events")
        self.assertIn("payment_request_observed", " ".join(logs.output))
        self.projection.apply.assert_not_awaited()
        message.ack.assert_awaited_once()

    async def test_success_is_dispatched_and_acknowledged_after_persistence(self):
        message = self.message(self.success)
        async def apply(event):
            message.ack.assert_not_awaited()
            self.assertEqual(event["payment_id"], self.success.payment_id)
            self.assertEqual(event["event_id"], self.success.event_id)
        self.projection.apply.side_effect = apply
        await self.bus.handle_message(message, self.registry, "application_events")
        self.projection.apply.assert_awaited_once()
        message.ack.assert_awaited_once()
        self.bus._forward.assert_not_awaited()

    async def test_supabase_outage_routes_to_delayed_retry_before_ack(self):
        message = self.message(self.success)
        self.projection.apply.side_effect = ConnectionError("Supabase unavailable")
        async def forward(original, destination, count):
            message.ack.assert_not_awaited()
            self.assertIs(original, message)
            self.assertEqual(destination, "application_events.retry.5")
            self.assertEqual(count, 1)
        self.bus._forward.side_effect = forward
        await self.bus.handle_message(message, self.registry, "application_events")
        message.ack.assert_awaited_once()
        message.nack.assert_not_awaited()

    async def test_unavailable_retry_destination_keeps_original_message(self):
        message = self.message(self.success)
        self.projection.apply.side_effect = ConnectionError("Supabase unavailable")
        self.bus._forward.side_effect = ConnectionError("RabbitMQ unavailable")
        await self.bus.handle_message(message, self.registry, "application_events")
        message.nack.assert_awaited_once_with(requeue=True)
        message.ack.assert_not_awaited()

    async def test_invalid_event_is_retained_in_dead_queue(self):
        message = self.message(self.success)
        message.body = b"{invalid json"
        await self.bus.handle_message(message, self.registry, "application_events")
        self.bus._forward.assert_awaited_once_with(message, "application_events.dead")
        message.ack.assert_awaited_once()
        self.projection.apply.assert_not_awaited()
