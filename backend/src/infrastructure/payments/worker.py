"""Confirmed delivery, delayed retries and separate payment/event consumers."""
import asyncio
from dataclasses import asdict
import json
import logging
import os

import aio_pika
from dotenv import load_dotenv

from src.application.use_cases.payments import ProcessPayment
from src.events.contracts.event_envelope import EventEnvelope
from src.events.contracts.payment_events import PaymentRequested, PaymentSucceeded
from src.infrastructure.payments.config import payment_store
from src.infrastructure.payments.stripe_gateway import StripeGateway


logger = logging.getLogger(__name__)
REQUESTS = "payments.requests"
SUCCESSES = "payments.projection"


class LocalPaymentProjection:
    """Working technical projection; final Supabase adapter uses the same contract."""
    def __init__(self, store):
        self.store = store

    async def apply(self, event):
        self.store.apply_projection(event)


class PaymentWorker:
    def __init__(self, store, gateway, projection=None):
        self.store = store
        self.processor = ProcessPayment(store, gateway)
        self.projection = projection or LocalPaymentProjection(store)

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
        for name, event_type in ((REQUESTS, PaymentRequested.EVENT_TYPE), (SUCCESSES, PaymentSucceeded.EVENT_TYPE)):
            queue = await self.channel.declare_queue(name, durable=True, arguments={"x-queue-type": "quorum"})
            await queue.bind(self.exchange, routing_key=event_type)
            self.queues[name] = queue
            await self.channel.declare_queue(name + ".dead", durable=True, arguments={"x-queue-type": "quorum"})
            for seconds in (5, 30, 300):
                await self.channel.declare_queue(f"{name}.retry.{seconds}", durable=True, arguments={
                    "x-queue-type": "quorum", "x-dead-letter-strategy": "at-least-once",
                    "x-overflow": "reject-publish",
                    "x-message-ttl": seconds * 1000, "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": name,
                })

    async def publish_outbox_once(self):
        for row in self.store.pending_events():
            envelope = EventEnvelope.from_json(row["body"])
            await self.exchange.publish(aio_pika.Message(
                row["body"].encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json", message_id=envelope.event_id,
            ), routing_key=envelope.event_type, mandatory=True)
            # Crash between publish and marking sent => duplicate, never lost message.
            self.store.mark_sent(row["event_id"])

    async def dispatch(self, body, name):
        envelope = EventEnvelope.from_json(body)
        if name == REQUESTS and envelope.event_type == PaymentRequested.EVENT_TYPE:
            event = PaymentRequested.from_payload(envelope.payload, event_id=envelope.event_id,
                                                   occurred_at=envelope.occurred_at)
            await self.processor.execute(event.payment_id)
        elif name == SUCCESSES and envelope.event_type == PaymentSucceeded.EVENT_TYPE:
            event = PaymentSucceeded.from_payload(envelope.payload, event_id=envelope.event_id,
                                                   occurred_at=envelope.occurred_at)
            await self.projection.apply(asdict(event) | {"occurred_at": event.occurred_at.isoformat()})
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
    if os.getenv("PAYMENTS_SANDBOX_FIXTURES", "false").lower() == "true" and not key.startswith("sk_test_"):
        raise RuntimeError("Sandbox fixtures require a Stripe test key")
    await PaymentWorker(payment_store(), StripeGateway(
        key, os.getenv("STRIPE_SUCCESS_URL"), os.getenv("STRIPE_CANCEL_URL"),
    )).run()


if __name__ == "__main__":
    asyncio.run(main())
