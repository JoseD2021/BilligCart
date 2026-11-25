import json
import logging
import os

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

from src.domain.errors import DomainError
from src.events.application.event_publisher import EventPublisher
from src.events.application.event_registry import EventRegistry
from src.events.contracts.base_event import BaseEvent
from src.events.contracts.event_envelope import EventEnvelope

logger = logging.getLogger(__name__)


class RabbitMQEventBus(EventPublisher):
    """
    Infraestructura genérica de eventos basada en RabbitMQ.

    Proporciona publicación y consumo; no contiene reglas
    específicas de ningún caso de uso.
    """

    def __init__(self) -> None:
        self.host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.username = os.getenv("RABBITMQ_USER")
        self.password = os.getenv("RABBITMQ_PASSWORD")
        self.virtual_host = os.getenv("RABBITMQ_VHOST", "/")

        self.exchange_name = os.getenv(
            "RABBITMQ_EVENT_EXCHANGE",
            "domain_events",
        )
        self.dead_letter_exchange_name = os.getenv(
            "RABBITMQ_EVENT_DEAD_LETTER_EXCHANGE",
            "domain_events.dlx",
        )

        self._connection = None
        self._channel = None
        self._exchange = None
        self._dead_letter_exchange = None

    async def connect(self) -> None:
        if self._connection and not self._connection.is_closed:
            return

        if not self.username or not self.password:
            raise RuntimeError(
                "Faltan RABBITMQ_USER o RABBITMQ_PASSWORD."
            )

        self._connection = await aio_pika.connect_robust(
            host=self.host,
            port=self.port,
            login=self.username,
            password=self.password,
            virtualhost=self.virtual_host,
            heartbeat=60,
        )

        self._channel = await self._connection.channel(publisher_confirms=True, on_return_raises=True)
        await self._channel.set_qos(prefetch_count=1)

        self._exchange = await self._channel.declare_exchange(
            self.exchange_name,
            ExchangeType.TOPIC,
            durable=True,
        )

        self._dead_letter_exchange = (
            await self._channel.declare_exchange(
                self.dead_letter_exchange_name,
                ExchangeType.TOPIC,
                durable=True,
            )
        )

    async def publish(self, event: BaseEvent) -> None:
        await self.connect()

        envelope = EventEnvelope.from_event(event)

        message = Message(
            body=envelope.to_json().encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=envelope.event_id,
            type=envelope.event_type,
        )

        await self._exchange.publish(
            message,
            routing_key=envelope.event_type,
        )

    async def prepare_consumer(
        self,
        registry: EventRegistry,
        queue_name: str | None = None,
    ):
        await self.connect()

        if not registry.event_types:
            raise ValueError(
                "No hay handlers registrados para consumir eventos."
            )

        queue_name = queue_name or os.getenv(
            "RABBITMQ_EVENT_QUEUE",
            "application_events",
        )

        # La cola principal envía los mensajes rechazados
        # a su dead-letter exchange.
        queue = await self._channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange":
                    self.dead_letter_exchange_name,
            },
        )

        # Cola duradera para inspeccionar mensajes fallidos.
        dead_queue = await self._channel.declare_queue(
            f"{queue_name}.dead",
            durable=True,
        )

        await dead_queue.bind(
            self._dead_letter_exchange,
            routing_key="#",
        )

        # Cada tipo registrado se enlaza con el topic exchange.
        for event_type in registry.event_types:
            await queue.bind(
                self._exchange,
                routing_key=event_type,
            )

        for seconds in (5, 30, 300):
            await self._channel.declare_queue(f"{queue_name}.retry.{seconds}", durable=True, arguments={
                "x-queue-type": "quorum", "x-dead-letter-strategy": "at-least-once",
                "x-overflow": "reject-publish", "x-message-ttl": seconds * 1000,
                "x-dead-letter-exchange": "", "x-dead-letter-routing-key": queue_name,
            })

        logger.info(
            "Consumiendo eventos desde la cola %s",
            queue_name,
        )
        return queue

    async def _forward(self, message, destination, retry_count=0):
        await self._channel.default_exchange.publish(Message(
            body=message.body, content_type="application/json", delivery_mode=DeliveryMode.PERSISTENT,
            message_id=message.message_id, headers={"retry_count": retry_count},
        ), routing_key=destination, mandatory=True)

    async def handle_message(self, message, registry, queue_name):
        try:
            envelope = EventEnvelope.from_json(message.body)
            logger.info("event_received event_type=%s event_id=%s queue=%s",
                        envelope.event_type, envelope.event_id, queue_name)
            await registry.dispatch(envelope)
        except (json.JSONDecodeError, ValueError, TypeError, KeyError, LookupError, DomainError):
            try:
                await self._forward(message, f"{queue_name}.dead")
            except Exception:
                await message.nack(requeue=True)
                return
            await message.ack()
            logger.exception("event_rejected event_id=%s destination=%s.dead", message.message_id, queue_name)
        except Exception:
            count = int((message.headers or {}).get("retry_count", 0))
            delay = (5, 30, 300)[min(count, 2)]
            try:
                await self._forward(message, f"{queue_name}.retry.{delay}", count + 1)
            except Exception:
                await message.nack(requeue=True)
                return
            await message.ack()
            logger.warning("event_retry_scheduled event_id=%s delay=%s queue=%s",
                           message.message_id, delay, queue_name)
        else:
            await message.ack()
            logger.info("event_processed event_type=%s event_id=%s queue=%s",
                        envelope.event_type, envelope.event_id, queue_name)

    async def consume(self, registry: EventRegistry, queue_name: str | None = None) -> None:
        queue = await self.prepare_consumer(registry, queue_name)

        async with queue.iterator() as iterator:
            async for message in iterator:
                await self.handle_message(message, registry, queue.name)

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

        self._connection = None
        self._channel = None
        self._exchange = None
        self._dead_letter_exchange = None
