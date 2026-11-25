"""Opt-in integration test against a real RabbitMQ, using isolated test queues."""
import asyncio
import functools
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from test_payments import ORDER, USER, Quotes, stripe_event
from test_supabase_payment_projection import Database

from src.application.use_cases.payments import Payments
from src.domain.entities.payment import PaymentStatus, PaymentUnavailable
from src.events.application.event_registry import EventRegistry
from src.events.application.payment_event_handlers import (
    on_payment_requested,
    on_payment_succeeded,
)
from src.events.contracts.payment_events import PaymentRequested, PaymentSucceeded
from src.events.infrastructure.rabbitmq_event_bus import RabbitMQEventBus
from src.infrastructure.payments.store import PaymentStore
from src.infrastructure.payments.stripe_gateway import receive_webhook
from src.infrastructure.payments.supabase_projection import SupabasePaymentProjection
from src.infrastructure.payments.worker import PaymentWorker


@unittest.skipUnless(os.getenv("PAYMENTS_BROKER_TEST") == "1", "Requires an explicitly enabled real RabbitMQ")
class BrokerTests(unittest.IsolatedAsyncioTestCase):
    async def test_general_event_consumer_persists_success_while_payment_worker_only_executes_stripe(self):
        prefix = "general_payment_test_" + uuid4().hex
        requests, old_successes, general = prefix + ".requests", prefix + ".old", prefix + ".events"
        with TemporaryDirectory() as directory, patch.dict(os.environ, {
            "RABBITMQ_EVENT_EXCHANGE": prefix, "RABBITMQ_EVENT_DEAD_LETTER_EXCHANGE": prefix + ".dlx",
        }), patch("src.infrastructure.payments.worker.REQUESTS", requests), patch(
            "src.infrastructure.payments.worker.SUCCESSES", old_successes,
        ):
            store = PaymentStore(str(Path(directory) / "journal.sqlite3"))
            payment = await Payments(store, Quotes()).request(USER, ORDER, "general-broker-key")
            database = Database()
            projection = SupabasePaymentProjection(store, database)
            registry = EventRegistry()
            registry.register(PaymentRequested, on_payment_requested)
            registry.register(PaymentSucceeded, functools.partial(on_payment_succeeded, projection=projection))
            general_bus = RabbitMQEventBus()
            queue = await general_bus.prepare_consumer(registry, general)
            gateway = SimpleNamespace(create_checkout=AsyncMock(side_effect=[
                PaymentUnavailable(), ("cs_test_example", "https://checkout.stripe.com/test"),
            ]))
            worker = PaymentWorker(store, gateway, process_successes=False)
            await worker.connect()
            try:
                self.assertEqual(set(worker.queues), {requests})
                await worker.publish_outbox_once()
                await general_bus.handle_message(await self.take(queue), registry, general)
                gateway.create_checkout.assert_not_awaited()
                self.assertEqual(database.rows, {})
                await worker.handle(await self.take(worker.queues[requests]), requests)
                self.assertEqual(store.get(payment.id).status, PaymentStatus.QUEUED)
                await worker.handle(await self.take(worker.queues[requests], seconds=12), requests)
                self.assertEqual(store.get(payment.id).status, PaymentStatus.READY)
                receive_webhook(store, stripe_event(payment))
                success = next(json.loads(row["body"]) for row in store.pending_events() if "payments.succeeded.v1" in row["body"])
                await worker.publish_outbox_once()
                database.fail_before_write = True
                await general_bus.handle_message(await self.take(queue), registry, general)
                self.assertEqual(database.rows, {})
                database.fail_before_write = False
                await general_bus.handle_message(await self.take(queue, seconds=12), registry, general)
                self.assertEqual(len(database.rows), 1)
                self.assertEqual(gateway.create_checkout.await_count, 2)  # One outage, one successful creation.
                duplicate = PaymentSucceeded.from_payload(success["payload"], event_id=success["event_id"],
                                                           occurred_at=success["occurred_at"])
                await general_bus.publish(duplicate)
                await general_bus.handle_message(await self.take(queue), registry, general)
                self.assertEqual(len(database.rows), 1)
                old_queue = await worker.channel.get_queue(old_successes)
                self.assertIsNone(await old_queue.get(fail=False))
            finally:
                for name in (requests, old_successes):
                    for suffix in ("", ".dead", ".retry.5", ".retry.30", ".retry.300"):
                        await worker.channel.queue_delete(name + suffix)
                for suffix in ("", ".dead", ".retry.5", ".retry.30", ".retry.300"):
                    await general_bus._channel.queue_delete(general + suffix)
                await general_bus._dead_letter_exchange.delete()
                await worker.exchange.delete()
                await worker.connection.close()
                await general_bus.close()

    async def test_real_broker_retains_retry_and_delivers_success_projection(self):
        prefix = "payment_test_" + uuid4().hex
        requests, projection = prefix + ".requests", prefix + ".projection"
        with TemporaryDirectory() as directory, patch.dict(os.environ, {"RABBITMQ_EVENT_EXCHANGE": prefix}), patch(
            "src.infrastructure.payments.worker.REQUESTS", requests,
        ), patch("src.infrastructure.payments.worker.SUCCESSES", projection):
            store = PaymentStore(str(Path(directory) / "journal.sqlite3"))
            payment = await Payments(store, Quotes()).request(USER, ORDER, "broker-test-key")
            gateway = SimpleNamespace(create_checkout=AsyncMock(side_effect=[
                PaymentUnavailable(), ("cs_test_example", "https://checkout.stripe.com/test"),
            ]))
            worker = PaymentWorker(store, gateway)
            await worker.connect()
            try:
                await worker.publish_outbox_once()
                original = await self.take(worker.queues[requests])
                await worker.handle(original, requests)
                self.assertEqual(store.get(payment.id).status, PaymentStatus.QUEUED)
                retried = await self.take(worker.queues[requests], seconds=12)
                await worker.handle(retried, requests)
                self.assertEqual(store.get(payment.id).status, PaymentStatus.READY)
                receive_webhook(store, stripe_event(payment))
                await worker.publish_outbox_once()
                event = await self.take(worker.queues[projection])
                await worker.handle(event, projection)
                with store.transaction() as db:
                    self.assertEqual(db.execute("SELECT count(*) FROM paid_orders").fetchone()[0], 1)
            finally:
                for name in (requests, projection):
                    for suffix in ("", ".dead", ".retry.5", ".retry.30", ".retry.300"):
                        await worker.channel.queue_delete(name + suffix)
                await worker.exchange.delete()
                await worker.connection.close()

    async def take(self, queue, seconds=5):
        for _ in range(seconds * 10):
            message = await queue.get(fail=False)
            if message:
                return message
            await asyncio.sleep(0.1)
        self.fail("Timed out waiting for RabbitMQ delivery")
