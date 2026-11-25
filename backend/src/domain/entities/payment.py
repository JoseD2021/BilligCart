from __future__ import annotations

"""Payment contracts, independent of the gateway and the final order schema."""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class PaymentStatus(StrEnum):
    QUEUED = "queued"
    READY = "ready"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"
    REVIEW = "review_required"


@dataclass(frozen=True)
class PaymentQuote:
    order_id: str
    user_id: str
    amount_minor: int
    currency: str
    version: str
    expires_at: datetime

    def __post_init__(self):
        if type(self.amount_minor) is not int or self.amount_minor <= 0:
            raise ValueError("A payment requires a positive integer amount in minor units.")
        if len(self.currency) != 3 or not self.currency.isascii() or not self.currency.isalpha():
            raise ValueError("Invalid currency code.")
        if self.expires_at.tzinfo is None:
            raise ValueError("Quote expiration must include a timezone.")


class PaymentUnavailable(Exception):
    """Temporary provider failure: retain the same request and idempotency key."""


class PaymentRejected(Exception):
    """Permanent provider or configuration error; do not retry automatically."""


@dataclass(frozen=True)
class Payment:
    id: str
    user_id: str
    order_id: str
    amount_minor: int
    currency: str
    quote_version: str
    quote_expires_at: float
    status: PaymentStatus
    created_at: float
    attempt: int
    provider_session_id: str | None = None
    checkout_url: str | None = None
    first_attempt_at: float | None = None
    error: str | None = None
    # Only replaced after explicit reconciliation of a definitively rejected request.
    # Automatic retries always reuse this stored key (or the original payment id).
    provider_idempotency_key: str | None = None
