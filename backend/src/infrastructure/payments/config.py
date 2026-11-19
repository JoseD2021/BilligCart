import os
from datetime import UTC, datetime, timedelta

from src.application.use_cases.payments import Payments
from src.domain.entities.payment import PaymentQuote
from src.domain.errors import OrderNotReady
from src.infrastructure.payments.store import PaymentStore
from src.infrastructure.payments.stripe_gateway import StripeGateway


class UnconfiguredQuotes:
    async def get(self, user_id, order_id):
        raise OrderNotReady("El cobro requiere precios finales y una cotizacion autorizada. Esa integracion esta pendiente.")


class SandboxQuotes:
    """Explicit test fixture. Never treats shopping reference prices as real totals."""
    def __init__(self, amount_minor=1000, currency="usd"):
        self.amount_minor, self.currency = amount_minor, currency

    async def get(self, user_id, order_id):
        return PaymentQuote(order_id, user_id, self.amount_minor, self.currency, "sandbox-fixture-v1",
                            datetime.now(UTC) + timedelta(hours=1))


def payment_store():
    return PaymentStore(os.getenv("PAYMENTS_JOURNAL_PATH", "./.payment-data/journal.sqlite3"))


def get_payments():
    sandbox = os.getenv("PAYMENTS_SANDBOX_FIXTURES", "false").lower() == "true"
    if sandbox:
        if not os.getenv("STRIPE_SECRET_KEY", "").startswith("sk_test_"):
            raise OrderNotReady("Las cotizaciones ficticias requieren una clave sk_test_ de Stripe.")
        quotes = SandboxQuotes()
    else:
        quotes = UnconfiguredQuotes()
    return Payments(payment_store(), quotes, StripeGateway(
        os.getenv("STRIPE_SECRET_KEY"), os.getenv("STRIPE_SUCCESS_URL"), os.getenv("STRIPE_CANCEL_URL")))
