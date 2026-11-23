"""Confirmed delivery, delayed retries and separate payment/event consumers."""
import asyncio
import json
import logging
import os
from dataclasses import asdict

import aio_pika
from dotenv import load_dotenv

from src.application.use_cases.payments import ProcessPayment
from src.events.contracts.event_envelope import EventEnvelope
from src.events.contracts.payment_events import PaymentRequested, PaymentSucceeded
from src.infrastructure.payments.config import payment_store
from src.infrastructure.payments.stripe_gateway import StripeGateway
from src.infrastructure.payments.supabase_projection import SupabasePaymentProjection

logger = logging.getLogger(__name__)
REQUESTS = "payments.requests"
SUCCESSES = "payments.projection"


class LocalPaymentProjection:
    """Isolated-test adapter; production successes are handled by event_worker."""
    target = "sqlite.paid_orders"
    def __init__(self, store):
        self.store = store

    async def apply(self, event):
        inserted = self.store.apply_projection(event)
        logger.info("payment_projection_%s target=sqlite.paid_orders event_id=%s payment_id=%s order_id=%s",
                    "applied" if inserted else "duplicate", event["event_id"], event["payment_id"], event["order_id"])


class PaymentWorker:
    def __init__(self, store, gateway, projection=None, *, process_successes=True):
        self.store = store
        self.processor = ProcessPayment(store, gateway)
        self.projection = projection or LocalPaymentProjection(store)
        self.process_successes = process_successes

    async def connect(self):
        self.connection = await aio_pika.connect_robust(
            host=os.getenv("RABBITMQ_HOST", "rabbitmq"), port=int(os.getenv("RABBITMQ_PORT", "5672")),
            login=os.environ["RABBITMQ_USER"], password=os.environ["RABBITMQ_PASSWORD"],
            virtualhost=os.getenv("RABBITMQ_VHOST", "/"), timeout=10,
        )
        self.channel = await self.connection.channel(publisher_confirms=True, on_return_raises=True)
        await self.channel.set_qos(prefetch_count=1)
        self.exchange = await self.channel.declare_exchange(
            os.getenv("RABBITMQ_EVENT_EXCHANGE", "domain_events"), aio_pika.ExchangeType.TOPIC, durable=True)
        self.queues = {}
        # Keep declaring the old success queue while migrating, so no durable message is discarded.
        for name, event_type in ((REQUESTS, PaymentRequested.EVENT_TYPE), (SUCCESSES, PaymentSucceeded.EVENT_TYPE)):
            queue = await self.channel.declare_queue(name, durable=True, arguments={"x-queue-type": "quorum"})
            if name == REQUESTS or self.process_successes:
                await queue.bind(self.exchange, routing_key=event_type)
            else:
                await queue.unbind(self.exchange, routing_key=event_type)
            if name == REQUESTS or self.process_successes:
                self.queues[name] = queue
            await self.channel.declare_queue(name + ".dead", durable=True, arguments={"x-queue-type": "quorum"})
            for seconds in (5, 30, 300):
                await self.channel.declare_queue(f"{name}.retry.{seconds}", durable=True, arguments={
                    "x-queue-type": "quorum", "x-dead-letter-strategy": "at-least-once",
                    "x-overflow": "reject-publish",
                    "x-message-ttl": seconds * 1000, "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": name,
                })
        logger.info("payment_worker_connected request_queue=%s success_consumer=%s",
                    REQUESTS, "local-test-consumer" if self.process_successes else "event_worker")

    async def publish_outbox_once(self):
        for row in self.store.pending_events():
            envelope = EventEnvelope.from_json(row["body"])
            await self.exchange.publish(aio_pika.Message(
                row["body"].encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json", message_id=envelope.event_id,
            ), routing_key=envelope.event_type, mandatory=True)
            # Crash between publish and marking sent => duplicate, never lost message.
            self.store.mark_sent(row["event_id"])
            logger.info("payment_event_published event_type=%s event_id=%s payment_id=%s",
                        envelope.event_type, envelope.event_id, envelope.payload.get("payment_id"))

    async def dispatch(self, body, name):
        envelope = EventEnvelope.from_json(body)
        logger.info("payment_event_received queue=%s event_type=%s event_id=%s payment_id=%s",
                    name, envelope.event_type, envelope.event_id, envelope.payload.get("payment_id"))
        if name == REQUESTS and envelope.event_type == PaymentRequested.EVENT_TYPE:
            event = PaymentRequested.from_payload(envelope.payload, event_id=envelope.event_id,
                                                   occurred_at=envelope.occurred_at)
            await self.processor.execute(event.payment_id)
            payment = self.store.get(event.payment_id)
            logger.info("payment_request_processed event_id=%s payment_id=%s status=%s",
                        event.event_id, event.payment_id, payment.status.value if payment else "not_found")
        elif self.process_successes and name == SUCCESSES and envelope.event_type == PaymentSucceeded.EVENT_TYPE:
            event = PaymentSucceeded.from_payload(envelope.payload, event_id=envelope.event_id,
                                                   occurred_at=envelope.occurred_at)
            await self.projection.apply(asdict(event) | {"occurred_at": event.occurred_at.isoformat()})
            logger.info("payment_success_consumed event_id=%s payment_id=%s order_id=%s",
                        event.event_id, event.payment_id, event.order_id)
        else:
            raise ValueError("Unexpected payment event")

    async def handle(self, message, name):
        try:
            await self.dispatch(message.body, name)
        except (json.JSONDecodeError, ValueError, TypeError, KeyError):
            try:
                await self.forward(message, name + ".dead")
            except Exception:
                await message.nack(requeue=True)
                return
            await message.ack()
            logger.error("payment_message_dead message_id=%s", message.message_id)
        except Exception:
            count = int((message.headers or {}).get("retry_count", 0))
            delay = (5, 30, 300)[min(count, 2)]
            try:
                await self.forward(message, f"{name}.retry.{delay}", count + 1)
            except Exception:
                # Original stays on the source queue when retry publication fails.
                await message.nack(requeue=True)
                return
            await message.ack()
            logger.warning("payment_message_retry message_id=%s delay=%s", message.message_id, delay)
        else:
            await message.ack()

    async def forward(self, message, queue, retry_count=0):
        await self.channel.default_exchange.publish(aio_pika.Message(
            message.body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json", message_id=message.message_id,
            headers={"retry_count": retry_count},
        ), routing_key=queue, mandatory=True)

    async def pump(self):
        while True:
            try:
                await self.publish_outbox_once()
            except Exception:
                logger.warning("payment_outbox_pending; retained for retry")
            await asyncio.sleep(2)

    async def run(self):
        while True:
            try:
                await self.connect()
                for name, queue in self.queues.items():
                    async def callback(message, queue_name=name):
                        await self.handle(message, queue_name)
                    await queue.consume(callback)
                await self.pump()
            except Exception:
                logger.warning("payment_bus_unavailable; reconnecting")
            finally:
                connection = getattr(self, "connection", None)
                if connection and not connection.is_closed:
                    await connection.close()
            await asyncio.sleep(5)


async def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if key and not key.startswith("sk_test_"):
        raise RuntimeError("Payments are enabled only with a Stripe sk_test_ key")
    store = payment_store()
    target = SupabasePaymentProjection.target
    pending = store.requeue_unprojected_successes(target)
    logger.info("payment_projection_backfill_queued target=%s count=%s consumer=event_worker", target, pending)
    await PaymentWorker(store, StripeGateway(
        key, os.getenv("STRIPE_SUCCESS_URL"), os.getenv("STRIPE_CANCEL_URL"),
    ), process_successes=False).run()


if __name__ == "__main__":
    asyncio.run(main())
