from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from src.events.contracts.base_event import BaseEvent


@dataclass(frozen=True, kw_only=True)
class PaymentRequested(BaseEvent):
    EVENT_TYPE: ClassVar[str] = "payments.requested.v1"
    payment_id: str


@dataclass(frozen=True, kw_only=True)
class PaymentSucceeded(BaseEvent):
    EVENT_TYPE: ClassVar[str] = "payments.succeeded.v1"
    payment_id: str
    order_id: str
    user_id: str
    amount_minor: int
    currency: str
    provider_session_id: str
