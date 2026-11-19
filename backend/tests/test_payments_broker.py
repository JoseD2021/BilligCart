"""Opt-in integration test against a real RabbitMQ, using isolated test queues."""
import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.domain.entities.payment import PaymentUnavailable, PaymentStatus
from src.infrastructure.payments.store import PaymentStore
from src.infrastructure.payments.worker import PaymentWorker
from src.infrastructure.payments.stripe_gateway import receive_webhook
from test_payments import Quotes, USER, ORDER, stripe_event
from src.application.use_cases.payments import Payments


@unittest.skipUnless(os.getenv("PAYMENTS_BROKER_TEST") == "1", "Requires an explicitly enabled real RabbitMQ")
class BrokerTests(unittest.IsolatedAsyncioTestCase):
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
