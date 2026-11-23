import hashlib
import hmac
import json
import time

import httpx

from src.domain.entities.payment import (
    PaymentRejected,
    PaymentStatus,
    PaymentUnavailable,
)


class StripeGateway:
    def __init__(self, secret_key, success_url, cancel_url, client=None):
        self.secret_key = secret_key
        self.success_url, self.cancel_url = success_url, cancel_url
        self.client = client

    async def create_checkout(self, payment):
        if not self.secret_key or not self.success_url or not self.cancel_url:
            raise PaymentUnavailable("Stripe configuration is missing")
        data = {
            "mode": "payment", "payment_method_types[0]": "card",
            "success_url": self.success_url, "cancel_url": self.cancel_url,
            "client_reference_id": payment.id, "metadata[payment_id]": payment.id,
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": payment.currency,
            "line_items[0][price_data][unit_amount]": str(payment.amount_minor),
            "line_items[0][price_data][product_data][name]": "BilligCart",
        }
        try:
            if self.client:
                response = await self._send(self.client, payment.id, data)
            else:
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await self._send(client, payment.id, data)
        except httpx.TransportError as exc:
            raise PaymentUnavailable("Stripe transport unavailable") from exc
        if response.status_code in (408, 409, 429) or response.status_code >= 500:
            raise PaymentUnavailable("Stripe temporarily unavailable")
        if not response.is_success:
            raise PaymentRejected("Stripe rejected checkout creation")
        try:
            result = response.json()
            if not result["id"].startswith("cs_") or not result["url"].startswith("https://checkout.stripe.com/"):
                raise ValueError("Unexpected checkout")
            return result["id"], result["url"]
        except (ValueError, KeyError, TypeError) as exc:
            raise PaymentUnavailable("Uncertain Stripe response; retry with the same key") from exc

    async def _send(self, client, key, data):
        return await client.post("https://api.stripe.com/v1/checkout/sessions", data=data,
                                 auth=httpx.BasicAuth(self.secret_key, ""), headers={
                                     "Idempotency-Key": key, "Stripe-Version": "2026-10-28.endive",
                                 })

    async def get_checkout(self, session_id):
        if not self.secret_key:
            raise PaymentUnavailable("Stripe configuration missing")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get("https://api.stripe.com/v1/checkout/sessions/" + session_id,
                                            auth=httpx.BasicAuth(self.secret_key, ""))
            if not response.is_success:
                raise PaymentUnavailable("Unable to reconcile Stripe session")
            return response.json()
        except (httpx.TransportError, ValueError) as exc:
            raise PaymentUnavailable("Unable to reconcile Stripe session") from exc


def verify_webhook(raw: bytes, signature: str, secret: str, *, now=None):
    if not secret or not signature:
        raise ValueError("Webhook configuration or signature missing")
    parts = [part.split("=", 1) for part in signature.split(",") if "=" in part]
    timestamps = [value for key, value in parts if key.strip() == "t"]
    signatures = [value for key, value in parts if key.strip() == "v1"]
    if len(timestamps) != 1:
        raise ValueError("Invalid timestamp")
    stamp = timestamps[0]
    if abs((time.time() if now is None else now) - int(stamp)) > 300:
        raise ValueError("Expired signature")
    expected = hmac.new(secret.encode(), stamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise ValueError("Invalid signature")
    event = json.loads(raw)
    if not isinstance(event, dict) or not isinstance(event.get("id"), str):
        raise TypeError("Invalid event")
    return event


def receive_webhook(store, event, *, livemode=False):
    types = {
        "checkout.session.completed": PaymentStatus.SUCCEEDED,
        "checkout.session.async_payment_succeeded": PaymentStatus.SUCCEEDED,
        "checkout.session.async_payment_failed": PaymentStatus.FAILED,
        "checkout.session.expired": PaymentStatus.EXPIRED,
    }
    status = types.get(event.get("type"))
    if status is None:
        return
    if event.get("livemode") is not livemode:
        raise ValueError("Wrong Stripe mode")
    session = event["data"]["object"]
    if status == PaymentStatus.SUCCEEDED and session.get("payment_status") != "paid":
        if event["type"] == "checkout.session.completed":
            status = PaymentStatus.PROCESSING
        else:
            raise ValueError("Success event without confirmed payment")
    payment_id = session.get("metadata", {}).get("payment_id")
    if not payment_id:
        # Other applications can use the same Stripe account.
        return
    store.webhook(event["id"], payment_id, session, status)
