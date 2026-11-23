import hashlib
import os
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from fastapi import Depends

from src.application.use_cases.payments import Payments
from src.domain.entities.payment import PaymentQuote
from src.domain.errors import OrderNotReady, ResourceNotFound
from src.infrastructure.api.v1.dependencies import get_pedido_repository
from src.infrastructure.payments.settings import PaymentSettings
from src.infrastructure.payments.store import PaymentStore
from src.infrastructure.payments.stripe_gateway import StripeGateway


class UnconfiguredQuotes:
    async def get(self, user_id, order_id):
        raise OrderNotReady("Los pagos TEST estan desactivados. Activa PAYMENTS_SANDBOX_FIXTURES=true para probarlos; los cobros reales siguen bloqueados.")


class TestOrderQuotes:
    """Owned order snapshot, charged only in Stripe TEST (no real funds)."""
    def __init__(self, orders, settings: PaymentSettings):
        self.orders, self.settings = orders, settings

    async def get(self, user_id, order_id):
        self.settings.require_ready()
        order = await self.orders.get_by_id(user_id, order_id)
        if order is None or str(order.user_id) != str(user_id):
            raise ResourceNotFound("Pedido no encontrado.")
        try:
            total = Decimal(str(order.total))
            if not total.is_finite() or total <= 0:
                raise OrderNotReady("El pedido debe tener un total positivo para probar el pago.")
            amount_minor = int((total * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise OrderNotReady("El total del pedido no es valido.") from exc
        if not 1 <= amount_minor <= 99999999:
            raise OrderNotReady("El total del pedido supera el rango admitido para la prueba de Stripe.")
        version = hashlib.sha256(f"{order.checkout_key}:{amount_minor}:{self.settings.currency}".encode()).hexdigest()
        return PaymentQuote(order_id, user_id, amount_minor, self.settings.currency, version,
                            datetime.now(UTC) + timedelta(hours=1))


def payment_store():
    return PaymentStore(os.getenv("PAYMENTS_JOURNAL_PATH", "./.payment-data/journal.sqlite3"))


def get_payments(orders=Depends(get_pedido_repository)):
    settings = PaymentSettings.from_env()
    if settings.sandbox:
        quotes = TestOrderQuotes(orders, settings)
    else:
        quotes = UnconfiguredQuotes()
    return Payments(payment_store(), quotes, StripeGateway(
        settings.secret_key, settings.success_url, settings.cancel_url))
