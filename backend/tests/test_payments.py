import asyncio
import hashlib
import hmac
import json
import os
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from src.application.use_cases.payments import Payments, ProcessPayment
from src.domain.entities.payment import PaymentQuote, PaymentStatus, PaymentUnavailable
from src.domain.entities.user import User
from src.domain.errors import OrderNotReady
from src.infrastructure.api.v1.app import create_app
from src.infrastructure.api.v1.dependencies import get_current_user
from src.infrastructure.payments.config import UnconfiguredQuotes, get_payments
from src.infrastructure.payments.store import PaymentStore
from src.infrastructure.payments.stripe_gateway import (
    StripeGateway,
    receive_webhook,
    verify_webhook,
)
from src.infrastructure.payments.worker import REQUESTS, SUCCESSES, PaymentWorker

USER = "00000000-0000-0000-0000-000000000001"
ORDER = "00000000-0000-0000-0000-000000000002"
SECRET = "whsec_unit_test_only"


class Quotes:
    async def get(self, user_id, order_id):
        return PaymentQuote(order_id, user_id, 1000, "usd", "final-quote-v1",
                            datetime.now(UTC) + timedelta(hours=1))


def signed(event, stamp=None):
    raw = json.dumps(event, separators=(",", ":")).encode()
    stamp = int(time.time()) if stamp is None else stamp
    signature = hmac.new(SECRET.encode(), str(stamp).encode() + b"." + raw, hashlib.sha256).hexdigest()
    return raw, f"t={stamp},v1={signature}"


def stripe_event(payment, type="checkout.session.completed", paid=True, event_id="evt_1"):
    return {"id": event_id, "type": type, "livemode": False, "data": {"object": {
        "id": "cs_test_example", "mode": "payment", "client_reference_id": payment.id,
        "metadata": {"payment_id": payment.id}, "amount_total": 1000, "currency": "usd",
        "payment_status": "paid" if paid else "unpaid",
    }}}


class PaymentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / "journal.sqlite3")
        self.store = PaymentStore(self.path)
        self.service = Payments(self.store, Quotes())

    async def payment(self, key="request-key-1"):
        return await self.service.request(USER, ORDER, key)

    async def test_idempotent_parallel_requests_and_process_restart(self):
        requests = await asyncio.gather(*(self.payment(f"request-key-{i}") for i in range(10)))
        self.assertEqual(len({p.id for p in requests}), 1)
        restarted = PaymentStore(self.path)
        self.assertEqual(restarted.current(USER, ORDER).id, requests[0].id)
        self.assertEqual(len(restarted.pending_events()), 1)

    async def test_quote_not_ready_blocks_charge_without_inventing_prices(self):
        with self.assertRaises(OrderNotReady):
            await Payments(self.store, UnconfiguredQuotes()).request(USER, ORDER, "request-key")
        self.assertEqual(self.store.pending_events(), [])

    async def test_outage_then_recovery_uses_same_stripe_idempotency_key(self):
        payment = await self.payment()
        keys = []
        def transport(request):
            keys.append(request.headers["Idempotency-Key"])
            if len(keys) == 1:
                return httpx.Response(503)
            self.assertIn(b"unit_amount%5D=1000", request.content)
            return httpx.Response(200, json={"id": "cs_test_example", "url": "https://checkout.stripe.com/test"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            processor = ProcessPayment(self.store, StripeGateway("sk_test_fake", "https://example.com/success", "https://example.com/cancel", client))
            with self.assertRaises(PaymentUnavailable):
                await processor.execute(payment.id)
            self.assertEqual(PaymentStore(self.path).get(payment.id).status, PaymentStatus.QUEUED)
            await processor.execute(payment.id)
        self.assertEqual(keys, [payment.id, payment.id])
        self.assertEqual(self.store.get(payment.id).status, PaymentStatus.READY)

    async def test_timeout_after_provider_acceptance_does_not_create_a_new_attempt(self):
        payment = await self.payment()
        gateway = SimpleNamespace(create_checkout=AsyncMock(side_effect=PaymentUnavailable()))
        with self.assertRaises(PaymentUnavailable):
            await ProcessPayment(self.store, gateway).execute(payment.id)
        retry = await self.payment("another-request-key")
        self.assertEqual(retry.id, payment.id)
        self.assertEqual(retry.attempt, 1)

    async def test_success_webhook_is_signed_idempotent_and_monotonic(self):
        payment = await self.payment()
        raw, signature = signed(stripe_event(payment))
        event = verify_webhook(raw, signature, SECRET)
        receive_webhook(self.store, event)
        receive_webhook(self.store, event)
        receive_webhook(self.store, stripe_event(payment, "checkout.session.expired", False, "evt_old"))
        self.assertEqual(self.store.get(payment.id).status, PaymentStatus.SUCCEEDED)
        self.assertEqual(len(self.store.pending_events()), 2)  # request + single success
        self.assertEqual((await self.payment("new-key-after-paid")).id, payment.id)

    async def test_bad_signature_old_signature_and_wrong_amount_never_confirm_payment(self):
        payment = await self.payment()
        raw, signature = signed(stripe_event(payment))
        for body, header in ((raw + b" ", signature), signed(stripe_event(payment), int(time.time()) - 301)):
            with self.assertRaises(ValueError):
                verify_webhook(body, header, SECRET)
        bad = stripe_event(payment)
        bad["data"]["object"]["amount_total"] = 1
        with self.assertRaises(ValueError):
            receive_webhook(self.store, bad)
        self.assertEqual(self.store.get(payment.id).status, PaymentStatus.QUEUED)

    async def test_unpaid_completion_waits_for_async_success(self):
        payment = await self.payment()
        receive_webhook(self.store, stripe_event(payment, paid=False))
        self.assertEqual(self.store.get(payment.id).status, PaymentStatus.PROCESSING)
        self.assertEqual(len(self.store.pending_events()), 1)
        receive_webhook(self.store, stripe_event(payment, "checkout.session.async_payment_succeeded", event_id="evt_paid"))
        self.assertEqual(self.store.get(payment.id).status, PaymentStatus.SUCCEEDED)

    async def test_terminal_failure_allows_new_attempt_but_same_http_key_returns_previous(self):
        payment = await self.payment()
        receive_webhook(self.store, stripe_event(payment, "checkout.session.async_payment_failed", False))
        self.assertEqual((await self.payment()).id, payment.id)
        self.service.gateway = SimpleNamespace(get_checkout=AsyncMock(return_value={"status": "expired", "payment_status": "unpaid"}))
        second = await self.payment("new-request-key")
        self.assertNotEqual(second.id, payment.id)
        self.assertEqual(second.attempt, 2)

    async def test_retry_reconciles_missed_success_instead_of_charging_again(self):
        payment = await self.payment()
        receive_webhook(self.store, stripe_event(payment, "checkout.session.expired", False))
        self.service.gateway = SimpleNamespace(get_checkout=AsyncMock(return_value=stripe_event(payment)["data"]["object"]))
        result = await self.payment("retry-after-missed-success")
        self.assertEqual(result.id, payment.id)
        self.assertEqual(result.status, PaymentStatus.SUCCEEDED)

    async def test_expiration_and_old_uncertain_attempt_require_safe_decisions(self):
        payment = await self.payment()
        self.store.update_queued(payment.id, quote_expires_at=time.time() - 1)
        gateway = SimpleNamespace(create_checkout=AsyncMock())
        await ProcessPayment(self.store, gateway).execute(payment.id)
        self.assertEqual(self.store.get(payment.id).status, PaymentStatus.EXPIRED)
        payment = await self.payment("new-request-key")
        self.store.update_queued(payment.id, first_attempt_at=time.time() - 24 * 3600)
        await ProcessPayment(self.store, gateway).execute(payment.id)
        self.assertEqual(self.store.get(payment.id).status, PaymentStatus.REVIEW)
        gateway.create_checkout.assert_not_awaited()

    async def test_broker_unavailable_keeps_outbox_until_confirmed(self):
        await self.payment()
        worker = PaymentWorker(self.store, None)
        worker.exchange = SimpleNamespace(publish=AsyncMock(side_effect=ConnectionError()))
        with self.assertRaises(ConnectionError):
            await worker.publish_outbox_once()
        self.assertEqual(len(PaymentStore(self.path).pending_events()), 1)
        worker.exchange.publish.side_effect = None
        await worker.publish_outbox_once()
        self.assertEqual(self.store.pending_events(), [])

    async def test_event_updates_local_information_system_once_and_survives_restart(self):
        payment = await self.payment()
        receive_webhook(self.store, stripe_event(payment))
        success = next(row for row in self.store.pending_events() if "payments.succeeded.v1" in row["body"])
        worker = PaymentWorker(self.store, None)
        await worker.dispatch(success["body"], SUCCESSES)
        await worker.dispatch(success["body"], SUCCESSES)
        with PaymentStore(self.path).transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM paid_orders").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT payment_id FROM paid_orders").fetchone()[0], payment.id)

    async def test_worker_delays_transient_errors_and_only_acks_after_forward(self):
        await self.payment()
        worker = PaymentWorker(self.store, SimpleNamespace(create_checkout=AsyncMock(side_effect=PaymentUnavailable())))
        worker.channel = SimpleNamespace(default_exchange=SimpleNamespace(publish=AsyncMock()))
        message = SimpleNamespace(body=self.store.pending_events()[0]["body"].encode(), headers={},
                                  message_id="event", ack=AsyncMock(), nack=AsyncMock())
        await worker.handle(message, REQUESTS)
        message.ack.assert_awaited_once()
        self.assertEqual(worker.channel.default_exchange.publish.call_args.kwargs["routing_key"], REQUESTS + ".retry.5")
        worker.channel.default_exchange.publish.side_effect = ConnectionError()
        message.ack.reset_mock()
        await worker.handle(message, REQUESTS)
        message.ack.assert_not_awaited()
        message.nack.assert_awaited_once_with(requeue=True)

    async def test_webhook_can_arrive_before_checkout_creation_response(self):
        payment = await self.payment()
        async def create(p):
            receive_webhook(self.store, stripe_event(p))
            return "cs_test_example", "https://checkout.stripe.com/test"
        await ProcessPayment(self.store, SimpleNamespace(create_checkout=create)).execute(payment.id)
        self.assertEqual(self.store.get(payment.id).status, PaymentStatus.SUCCEEDED)


class PaymentApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = PaymentStore(str(Path(self.directory.name) / "journal.sqlite3"))
        self.app = create_app()
        self.app.dependency_overrides[get_current_user] = lambda: User(USER, "user@example.com")
        self.app.dependency_overrides[get_payments] = lambda: Payments(self.store, Quotes())
        self.client = TestClient(self.app)

    def test_http_request_signed_webhook_and_user_success_message(self):
        response = self.client.post("/v1/pagos", json={"order_id": ORDER}, headers={"Idempotency-Key": "http-key-1"})
        self.assertEqual(response.status_code, 202, response.text)
        payment = self.store.get(response.json()["id"])
        raw, signature = signed(stripe_event(payment))
        with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": SECRET, "STRIPE_SECRET_KEY": "sk_test_test"}), patch(
            "src.infrastructure.api.v1.endpoints.payments.payment_store", return_value=self.store,
        ):
            response = self.client.post("/v1/pagos/webhook/stripe", content=raw, headers={"Stripe-Signature": signature})
        self.assertEqual(response.status_code, 200, response.text)
        response = self.client.get(f"/v1/pagos/pedido/{ORDER}")
        self.assertEqual(response.json()["status"], "succeeded")
        self.assertIn("exitoso", response.json()["message"])

    def test_client_cannot_choose_amount_and_other_users_cannot_read_payment(self):
        response = self.client.post("/v1/pagos", json={"order_id": ORDER, "amount_minor": 1}, headers={"Idempotency-Key": "http-key-1"})
        self.assertEqual(response.status_code, 422)
        self.client.post("/v1/pagos", json={"order_id": ORDER}, headers={"Idempotency-Key": "http-key-1"})
        self.app.dependency_overrides[get_current_user] = lambda: User("other", "other@example.com")
        self.assertIsNone(self.client.get(f"/v1/pagos/pedido/{ORDER}").json())
