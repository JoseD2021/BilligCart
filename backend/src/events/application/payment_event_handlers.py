import logging
from dataclasses import asdict

from src.application.interfaces.payments import PaymentProjection
from src.events.contracts.payment_events import PaymentRequested, PaymentSucceeded

logger = logging.getLogger(__name__)


async def on_payment_requested(event: PaymentRequested) -> None:
    # The general worker observes the event. Stripe execution belongs to payment_worker.
    logger.info("payment_request_observed event_id=%s payment_id=%s", event.event_id, event.payment_id)


async def on_payment_succeeded(event: PaymentSucceeded, projection: PaymentProjection) -> None:
    logger.info("payment_success_received event_id=%s payment_id=%s order_id=%s",
                event.event_id, event.payment_id, event.order_id)
    await projection.apply(asdict(event) | {"occurred_at": event.occurred_at.isoformat()})
    logger.info("payment_success_consumed event_id=%s payment_id=%s order_id=%s",
                event.event_id, event.payment_id, event.order_id)
