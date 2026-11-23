import json
import os
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi.testclient import TestClient

from src.application.use_cases.payments import Payments, ProcessPayment
from src.domain.entities.payment import PaymentRejected, PaymentStatus
from src.domain.entities.user import User
from src.domain.errors import OrderNotReady, ResourceNotFound
from src.infrastructure.api.v1.app import create_app
from src.infrastructure.api.v1.dependencies import get_current_user
from src.infrastructure.payments.config import TestOrderQuotes as OrderQuoteSource
from src.infrastructure.payments.config import get_payments
from src.infrastructure.payments.settings import PaymentSettings, get_payment_settings
from src.infrastructure.payments.store import PaymentStore
from src.infrastructure.payments.stripe_gateway import StripeGateway
from src.infrastructure.payments.worker import SUCCESSES, PaymentWorker

USER = "00000000-0000-0000-0000-000000000001"
ORDER = "00000000-0000-0000-0000-000000000002"
SETTINGS = PaymentSettings("sk_test_configuration_only", "whsec_configuration_only",
                           "http://localhost:8081/?existing=yes", "http://localhost:8081/", True, "cop")


class ConfigurationTests(unittest.TestCase):
    def test_public_configuration_never_exposes_secret_values(self):
        public = SETTINGS.public()
        self.assertTrue(public["ready"])
        self.assertEqual(public["amount_source"], "order_total")
        for secret in (SETTINGS.secret_key, SETTINGS.webhook_secret):
            self.assertNotIn(secret, json.dumps(public))

    def test_missing_keys_and_live_keys_are_actionable_and_blocked(self):
        missing = replace(SETTINGS, secret_key="", webhook_secret="")
        self.assertFalse(missing.public()["ready"])
        self.assertIn("STRIPE_SECRET_KEY", " ".join(missing.issues()))
        with self.assertRaises(OrderNotReady):
            missing.require_ready()
        with self.assertRaises(OrderNotReady):
            replace(SETTINGS, secret_key="sk_live_configuration_only").require_ready()
        with self.assertRaises(OrderNotReady):
            replace(SETTINGS, currency="usd").require_ready()

    def test_local_return_urls_keep_existing_query_and_identify_order(self):
        value = StripeGateway._return_url(SETTINGS.success_url, ORDER, "success")
        params = parse_qs(urlsplit(value).query)
        self.assertEqual(params["existing"], ["yes"])
        self.assertEqual(params["payment_order_id"], [ORDER])
        self.assertEqual(params["stripe_return"], ["success"])

    def test_configuration_endpoint_returns_no_credentials(self):
        app = create_app()
        app.dependency_overrides[get_current_user] = lambda: User(USER, "user@example.com")
        app.dependency_overrides[get_payment_settings] = lambda: SETTINGS
        response = TestClient(app).get("/v1/pagos/configuracion")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SETTINGS.secret_key, response.text)


class OrderQuoteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.order = SimpleNamespace(user_id=USER, total=Decimal("15000.25"), checkout_key="order-snapshot")
        self.orders = SimpleNamespace(get_by_id=AsyncMock(return_value=self.order))
        self.quotes = OrderQuoteSource(self.orders, SETTINGS)

    async def test_reads_owned_order_total_and_converts_cop_to_minor_units(self):
        quote = await self.quotes.get(USER, ORDER)
        self.assertEqual(quote.amount_minor, 1500025)
        self.assertEqual(quote.currency, "cop")
        self.orders.get_by_id.assert_awaited_once_with(USER, ORDER)

    async def test_missing_or_foreign_order_cannot_be_paid(self):
        for order in (None, SimpleNamespace(user_id="another-user")):
            self.orders.get_by_id.return_value = order
            with self.assertRaises(ResourceNotFound):
                await self.quotes.get(USER, ORDER)

    async def test_invalid_total_or_missing_configuration_never_creates_quote(self):
        for total in (0, -1, float("nan"), float("inf"), "bad", 1000000):
            self.order.total = total
            with self.subTest(total=total), self.assertRaises(OrderNotReady):
                await self.quotes.get(USER, ORDER)
        self.orders.get_by_id.reset_mock()
        with self.assertRaises(OrderNotReady):
            await OrderQuoteSource(self.orders, replace(SETTINGS, webhook_secret="")).get(USER, ORDER)
        self.orders.get_by_id.assert_not_awaited()

    async def test_live_key_cannot_send_checkout_even_for_previously_queued_payment(self):
        with self.assertRaises(PaymentRejected):
            await StripeGateway("sk_live_forbidden", SETTINGS.success_url, SETTINGS.cancel_url).create_checkout(None)

    async def test_full_test_order_http_checkout_signed_webhook_event_flow(self):
        with TemporaryDirectory() as directory:
            store = PaymentStore(str(Path(directory) / "journal.sqlite3"))
            service = Payments(store, self.quotes)
            app = create_app()
            app.dependency_overrides[get_current_user] = lambda: User(USER, "user@example.com")
            app.dependency_overrides[get_payments] = lambda: service
            client = TestClient(app)
            response = client.post("/v1/pagos", json={"order_id": ORDER}, headers={"Idempotency-Key": "order-total-key"})
            self.assertEqual(response.status_code, 202, response.text)
            payment = store.get(response.json()["id"])

            def transport(request):
                params = parse_qs(request.content.decode())
                self.assertFalse(any(name.startswith("payment_method_types") for name in params))
                self.assertEqual(params["line_items[0][price_data][unit_amount]"], ["1500025"])
                self.assertEqual(params["line_items[0][price_data][currency]"], ["cop"])
                self.assertEqual(request.headers["Idempotency-Key"], payment.id)
                return httpx.Response(200, json={"id": "cs_test_order_total", "url": "https://checkout.stripe.com/test"})

            async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
                gateway = StripeGateway(SETTINGS.secret_key, SETTINGS.success_url, SETTINGS.cancel_url, http)
                await ProcessPayment(store, gateway).execute(payment.id)
            self.assertEqual(client.get(f"/v1/pagos/pedido/{ORDER}").json()["status"], "ready")

            import hashlib
            import hmac
            import time
            payload = json.dumps({"id": "evt_order_total", "type": "checkout.session.completed", "livemode": False,
                                  "data": {"object": {"id": "cs_test_order_total", "mode": "payment",
                                           "metadata": {"payment_id": payment.id}, "client_reference_id": payment.id,
                                           "payment_status": "paid", "amount_total": 1500025, "currency": "cop"}}}).encode()
            timestamp = str(int(time.time()))
            digest = hmac.new(SETTINGS.webhook_secret.encode(), timestamp.encode() + b"." + payload, hashlib.sha256).hexdigest()
            with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": SETTINGS.webhook_secret}), patch(
                "src.infrastructure.api.v1.endpoints.payments.payment_store", return_value=store,
            ):
                result = client.post("/v1/pagos/webhook/stripe", content=payload,
                                     headers={"Stripe-Signature": f"t={timestamp},v1={digest}"})
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(client.get(f"/v1/pagos/pedido/{ORDER}").json()["status"], PaymentStatus.SUCCEEDED)
            success = next(row for row in store.pending_events() if "payments.succeeded.v1" in row["body"])
            await PaymentWorker(store, None).dispatch(success["body"], SUCCESSES)
            with store.transaction() as db:
                self.assertEqual(db.execute("SELECT payment_id FROM paid_orders WHERE order_id=?", (ORDER,)).fetchone()[0], payment.id)

    async def test_provider_rejection_keeps_safe_diagnostics_without_secret_payload(self):
        with TemporaryDirectory() as directory:
            store = PaymentStore(str(Path(directory) / "journal.sqlite3"))
            payment = await Payments(store, self.quotes).request(USER, ORDER, "diagnostic-request")
            def transport(request):
                return httpx.Response(400, headers={"request-id": "req_diagnostic"}, json={"error": {
                    "type": "invalid_request_error", "param": "payment_method_types",
                    "message": "Sensitive provider message " + SETTINGS.secret_key,
                }})
            async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
                gateway = StripeGateway(SETTINGS.secret_key, SETTINGS.success_url, SETTINGS.cancel_url, http)
                with self.assertLogs("src.infrastructure.payments.stripe_gateway", level="WARNING") as logs:
                    await ProcessPayment(store, gateway).execute(payment.id)
            result = store.get(payment.id)
            self.assertEqual(result.status, PaymentStatus.REVIEW)
            self.assertIn("payment_method_types", result.error)
            self.assertIn("req_diagnostic", result.error)
            self.assertNotIn(SETTINGS.secret_key, result.error)
            self.assertNotIn(SETTINGS.secret_key, " ".join(logs.output))

    async def test_reconciled_provider_key_remains_stable_during_automatic_retries(self):
        with TemporaryDirectory() as directory:
            store = PaymentStore(str(Path(directory) / "journal.sqlite3"))
            payment = await Payments(store, self.quotes).request(USER, ORDER, "reconciled-request")
            reconciled_key = payment.id + "-reviewed-request"
            store.update_queued(payment.id, provider_idempotency_key=reconciled_key)
            keys = []
            def transport(request):
                keys.append(request.headers["Idempotency-Key"])
                if len(keys) == 1:
                    return httpx.Response(503)
                return httpx.Response(200, json={"id": "cs_test_reconciled", "url": "https://checkout.stripe.com/test"})
            async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
                gateway = StripeGateway(SETTINGS.secret_key, SETTINGS.success_url, SETTINGS.cancel_url, http)
                processor = ProcessPayment(store, gateway)
                from src.domain.entities.payment import PaymentUnavailable
                with self.assertRaises(PaymentUnavailable):
                    await processor.execute(payment.id)
                await processor.execute(payment.id)
            self.assertEqual(keys, [reconciled_key, reconciled_key])
            self.assertEqual(PaymentStore(store.path).get(payment.id).id, payment.id)

    async def test_success_logs_correlate_event_and_committed_projection_without_duplicates(self):
        from src.infrastructure.payments.stripe_gateway import receive_webhook
        with TemporaryDirectory() as directory, self.assertLogs("src.infrastructure.payments", level="INFO") as logs:
            store = PaymentStore(str(Path(directory) / "journal.sqlite3"))
            payment = await Payments(store, self.quotes).request(USER, ORDER, "observable-request")
            receive_webhook(store, {"id": "evt_observable", "type": "checkout.session.completed", "livemode": False,
                                   "data": {"object": {"id": "cs_test_observable", "mode": "payment",
                                            "metadata": {"payment_id": payment.id}, "client_reference_id": payment.id,
                                            "payment_status": "paid", "amount_total": 1500025, "currency": "cop"}}})
            success = next(row for row in store.pending_events() if "payments.succeeded.v1" in row["body"])
            worker = PaymentWorker(store, None)
            worker.exchange = SimpleNamespace(publish=AsyncMock())
            await worker.publish_outbox_once()
            await worker.dispatch(success["body"], SUCCESSES)
            await worker.dispatch(success["body"], SUCCESSES)
            with store.transaction() as db:
                self.assertEqual(db.execute("SELECT count(*) FROM paid_orders").fetchone()[0], 1)
        output = "\n".join(logs.output)
        for step in ("payment_request_recorded", "stripe_webhook_applied", "payment_event_recorded",
                     "payment_event_published", "payment_event_received", "payment_projection_applied",
                     "payment_projection_duplicate", "payment_success_consumed"):
            self.assertIn(step, output)
        self.assertIn(payment.id, output)
        self.assertIn(success["event_id"], output)
        self.assertIn("target=sqlite.paid_orders", output)
        self.assertEqual(output.count("payment_projection_applied"), 1)
        self.assertNotIn(SETTINGS.secret_key, output)
        self.assertNotIn(SETTINGS.webhook_secret, output)
