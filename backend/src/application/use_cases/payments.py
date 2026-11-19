import time
from datetime import UTC, datetime

from src.application.interfaces.payments import PaymentGateway, QuoteSource
from src.domain.entities.payment import (
    PaymentRejected,
    PaymentStatus,
    PaymentUnavailable,
)
from src.domain.errors import InvalidRequestBodyError, OrderNotReady, ResourceNotFound


class Payments:
    def __init__(self, store, quotes: QuoteSource, gateway: PaymentGateway | None = None):
        self.store, self.quotes, self.gateway = store, quotes, gateway

    async def request(self, user_id, order_id, key):
        existing = self.store.by_key(user_id, key)
        if existing:
            if existing.order_id != order_id:
                raise InvalidRequestBodyError("Idempotency-Key ya pertenece a otro pedido.")
            return existing
        current = self.store.current(user_id, order_id)
        if current and current.status in (PaymentStatus.FAILED, PaymentStatus.EXPIRED) and current.provider_session_id:
            if self.gateway is None:
                raise OrderNotReady("Se requiere conciliar el intento anterior con Stripe antes de reintentar.")
            session = await self.gateway.get_checkout(current.provider_session_id)
            if session.get("payment_status") == "paid":
                self.store.webhook("reconciled-success:" + session["id"], current.id, session, PaymentStatus.SUCCEEDED)
                return self.store.get(current.id)
            if session.get("status") != "expired" or session.get("payment_status") != "unpaid":
                raise OrderNotReady("El intento anterior sigue pendiente de confirmacion en Stripe.")
        quote = await self.quotes.get(user_id, order_id)
        if quote.user_id != user_id or quote.order_id != order_id:
            raise ResourceNotFound("Pedido no encontrado.")
        if quote.expires_at <= datetime.now(UTC):
            raise OrderNotReady("La cotizacion final ha vencido.")
        return self.store.create(quote, key)

    def current(self, user_id, order_id):
        return self.store.current(user_id, order_id)


class ProcessPayment:
    def __init__(self, store, gateway: PaymentGateway):
        self.store, self.gateway = store, gateway

    async def execute(self, payment_id):
        payment = self.store.get(payment_id)
        if payment is None or payment.status != PaymentStatus.QUEUED:
            return
        now = time.time()
        if payment.first_attempt_at and now - payment.first_attempt_at > 23 * 3600:
            # Stripe may prune idempotency keys after 24h. Never create a new charge blindly.
            self.store.update_queued(payment_id, status=PaymentStatus.REVIEW, error="Requiere conciliacion con Stripe.")
            return
        if not payment.first_attempt_at and now >= payment.quote_expires_at:
            self.store.update_queued(payment_id, status=PaymentStatus.EXPIRED, error="La cotizacion vencio antes del envio.")
            return
        payment = self.store.update_queued(payment_id, first_attempt_at=payment.first_attempt_at or now)
        try:
            session_id, url = await self.gateway.create_checkout(payment)
        except PaymentUnavailable:
            self.store.update_queued(payment_id, error="Stripe temporalmente no disponible; solicitud conservada.")
            raise
        except PaymentRejected:
            # Unknown results/configuration errors require reconciliation, not a new charge.
            self.store.update_queued(payment_id, status=PaymentStatus.REVIEW,
                                     error="Stripe rechazo la solicitud. Requiere revision.")
            return
        self.store.update_queued(payment_id, status=PaymentStatus.READY,
                                 provider_session_id=session_id, checkout_url=url, error=None)
