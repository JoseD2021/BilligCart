from typing import Protocol

from src.domain.entities.payment import Payment, PaymentQuote


class QuoteSource(Protocol):
    async def get(self, user_id: str, order_id: str) -> PaymentQuote:
        """Authorize ownership and provide a final, immutable server-side quote."""
        ...


class PaymentGateway(Protocol):
    async def create_checkout(self, payment: Payment) -> tuple[str, str]:
        """Return provider reference and checkout URL using a stable idempotency key."""
        ...

    async def get_checkout(self, session_id: str) -> dict:
        """Retrieve canonical provider state before replacing a terminal attempt."""
        ...


class PaymentProjection(Protocol):
    async def apply(self, event: dict) -> None:
        """Atomically deduplicate event_id and update the information system."""
        ...
