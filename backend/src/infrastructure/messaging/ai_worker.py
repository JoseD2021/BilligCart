import asyncio
import json
import logging
import os
import time
from uuid import uuid4

import aio_pika
from aio_pika import DeliveryMode, Message
from dotenv import load_dotenv

from src.events.contracts.ai_menu_events import (
    MenuGenerationCompleted,
    MenuGenerationFailed,
    MenuGenerationStarted,
)
from src.events.infrastructure.rabbitmq_event_bus import RabbitMQEventBus
from src.infrastructure.ai.ollama import OllamaClient


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def publish_event_safely(
    event_bus: RabbitMQEventBus,
    event,
) -> None:
    """
    Los eventos de seguimiento no deben impedir que la IA
    devuelva el resultado por el canal de petición-respuesta.
    """
    try:
        await event_bus.publish(event)
    except Exception:
        logger.exception(
            "No se pudo publicar el evento %s",
            event.event_type,
        )


async def send_response(
    channel,
    reply_to: str,
    correlation_id: str,
    payload: dict,
) -> None:
    await channel.default_exchange.publish(
        Message(
            body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
            correlation_id=correlation_id,
            delivery_mode=DeliveryMode.PERSISTENT,
        ),
        routing_key=reply_to,
    )


async def process_message(
    message,
    channel,
    ollama_client: OllamaClient,
    event_bus: RabbitMQEventBus,
) -> None:
    async with message.process(requeue=False):
        request_id = message.correlation_id or str(uuid4())
        model = ollama_client.model

        try:
            request_data = json.loads(message.body.decode("utf-8"))
            prompt = request_data.get("prompt")

            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("El prompt es obligatorio.")

            await publish_event_safely(
                event_bus,
                MenuGenerationStarted(
                    request_id=request_id,
                    model=model,
                ),
            )

            started_at = time.monotonic()

            try:
                # requests es síncrono; lo ejecutamos fuera del
                # event loop para que no bloquee al consumidor.
                generated_menu = await asyncio.to_thread(
                    ollama_client.generate_response,
                    prompt,
                )

            except Exception as exc:
                await publish_event_safely(
                    event_bus,
                    MenuGenerationFailed(
                        request_id=request_id,
                        model=model,
                        error_type=type(exc).__name__,
                    ),
                )

                result = {
                    "status": "error",
                    "error": "No fue posible generar el menú.",
                }

                logger.exception(
                    "Falló la generación de menú. request_id=%s",
                    request_id,
                )

            else:
                duration_ms = int(
                    (time.monotonic() - started_at) * 1000
                )

                await publish_event_safely(
                    event_bus,
                    MenuGenerationCompleted(
                        request_id=request_id,
                        model=model,
                        duration_ms=duration_ms,
                    ),
                )

                result = {
                    "status": "success",
                    "response": generated_menu,
                }

                logger.info(
                    "Generación completada. request_id=%s duration_ms=%s",
                    request_id,
                    duration_ms,
                )

        except Exception as exc:
            await publish_event_safely(
                event_bus,
                MenuGenerationFailed(
                    request_id=request_id,
                    model=model,
                    error_type=type(exc).__name__,
                ),
            )

            result = {
                "status": "error",
                "error": str(exc),
            }

            logger.warning(
                "Solicitud inválida o fallida. request_id=%s type=%s",
                request_id,
                type(exc).__name__,
            )

        # Respondemos usando el contrato que ya conoce
        # RabbitMQAIClient, sin convertir la respuesta en un evento.
        if message.reply_to:
            await send_response(
                channel=channel,
                reply_to=message.reply_to,
                correlation_id=request_id,
                payload=result,
            )


async def main() -> None:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    username = os.getenv("RABBITMQ_USER")
    password = os.getenv("RABBITMQ_PASSWORD")
    queue_name = os.getenv("RABBITMQ_QUEUE", "ai_requests")
    virtual_host = os.getenv("RABBITMQ_VHOST", "/")

    if not username or not password:
        raise RuntimeError(
            "Debes configurar RABBITMQ_USER y RABBITMQ_PASSWORD."
        )

    ollama_client = OllamaClient()
    event_bus = RabbitMQEventBus()

    connection = await aio_pika.connect_robust(
        host=host,
        port=port,
        login=username,
        password=password,
        virtualhost=virtual_host,
        heartbeat=60,
    )

    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)

        queue = await channel.declare_queue(
            queue_name,
            durable=True,
        )

        async def on_message(message) -> None:
            await process_message(
                message=message,
                channel=channel,
                ollama_client=ollama_client,
                event_bus=event_bus,
            )

        await queue.consume(on_message)

        logger.info(
            "AI Worker escuchando en la cola %s con modelo %s",
            queue_name,
            ollama_client.model,
        )

        # Mantiene vivo el proceso hasta que se detenga.
        await asyncio.Future()

    finally:
        await event_bus.close()
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())