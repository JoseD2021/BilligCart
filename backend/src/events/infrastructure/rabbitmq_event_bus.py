import logging
import os

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

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

        self._channel = await self._connection.channel()
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

    async def consume(
        self,
        registry: EventRegistry,
        queue_name: str | None = None,
    ) -> None:
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

        logger.info(
            "Consumiendo eventos desde la cola %s",
            queue_name,
        )

        async with queue.iterator() as iterator:
            async for message in iterator:
                try:
                    async with message.process(requeue=False):
                        envelope = EventEnvelope.from_json(
                            message.body
                        )
                        await registry.dispatch(envelope)

                except Exception:
                    logger.exception(
                        "No se pudo procesar el evento %s. "
                        "RabbitMQ lo rechazará y lo enviará a la DLQ.",
                        message.message_id,
                    )

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

        self._connection = None
        self._channel = None
        self._exchange = None
        self._dead_letter_exchange = None