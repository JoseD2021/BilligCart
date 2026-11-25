"""Validate Stripe TEST configuration without exposing credentials."""
import os
from dataclasses import dataclass
from urllib.parse import urlparse

from src.domain.errors import OrderNotReady


@dataclass(frozen=True)
class PaymentSettings:
    secret_key: str
    webhook_secret: str
    success_url: str
    cancel_url: str
    sandbox: bool
    currency: str

    @classmethod
    def from_env(cls):
        return cls(
            os.getenv("STRIPE_SECRET_KEY", "").strip(),
            os.getenv("STRIPE_WEBHOOK_SECRET", "").strip(),
            os.getenv("STRIPE_SUCCESS_URL", "").strip(),
            os.getenv("STRIPE_CANCEL_URL", "").strip(),
            os.getenv("PAYMENTS_SANDBOX_FIXTURES", "false").lower() == "true",
            os.getenv("PAYMENTS_TEST_CURRENCY", "cop").strip().lower(),
        )

    def issues(self):
        issues = []
        if not self.secret_key:
            issues.append("Completa STRIPE_SECRET_KEY en backend/.env con tu clave sk_test_.")
        elif not self.secret_key.startswith("sk_test_"):
            issues.append("Esta integracion de prueba requiere STRIPE_SECRET_KEY de tipo sk_test_.")
        if not self.webhook_secret.startswith("whsec_"):
            issues.append("Completa STRIPE_WEBHOOK_SECRET con el whsec_ del listener o endpoint de Stripe.")
        for name, value in (("STRIPE_SUCCESS_URL", self.success_url), ("STRIPE_CANCEL_URL", self.cancel_url)):
            url = urlparse(value)
            if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
                issues.append(f"Configura {name} con una URL http o https valida de tu frontend.")
        if not self.sandbox:
            issues.append("Activa PAYMENTS_SANDBOX_FIXTURES=true para habilitar los pagos de prueba.")
        if self.currency != "cop":
            issues.append("PAYMENTS_TEST_CURRENCY debe ser cop: los totales del pedido estan expresados en pesos colombianos.")
        return issues

    def require_ready(self):
        issues = self.issues()
        if issues:
            raise OrderNotReady(" ".join(issues))

    def public(self):
        issues = self.issues()
        return {"ready": not issues, "mode": "test", "issues": issues,
                "currency": self.currency, "amount_source": "order_total",
                "requires_webhook": True}


def get_payment_settings():
    return PaymentSettings.from_env()
