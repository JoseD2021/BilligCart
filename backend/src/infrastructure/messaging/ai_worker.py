import json
import logging
import os
import time

import pika
from pika.exceptions import AMQPConnectionError

from src.infrastructure.ai.ollama import OllamaClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("ai-worker")


RABBITMQ_HOST = os.getenv(
    "RABBITMQ_HOST",
    "rabbitmq"
)

RABBITMQ_PORT = int(
    os.getenv("RABBITMQ_PORT", "5672")
)

RABBITMQ_USER = os.getenv(
    "RABBITMQ_USER",
    "billigcart"
)

RABBITMQ_PASSWORD = os.getenv(
    "RABBITMQ_PASSWORD",
    "billigcart123"
)

RABBITMQ_QUEUE = os.getenv(
    "RABBITMQ_QUEUE",
    "ai_requests"
)


def create_connection():

    credentials = pika.PlainCredentials(
        RABBITMQ_USER,
        RABBITMQ_PASSWORD
    )

    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=60,
        connection_attempts=5,
        retry_delay=2
    )

    return pika.BlockingConnection(parameters)


def start_worker():

    ollama_client = OllamaClient(
        base_url=os.getenv(
            "OLLAMA_BASE_URL",
            "http://ollama:11434"
        )
    )

    while True:

        connection = None

        try:

            logger.info(
                "Conectando a RabbitMQ..."
            )

            connection = create_connection()

            channel = connection.channel()

            channel.queue_declare(
                queue=RABBITMQ_QUEUE,
                durable=True
            )

            channel.basic_qos(
                prefetch_count=1
            )

            logger.info(
                "AI Worker conectado. "
                "Esperando mensajes..."
            )

            def process_message(
                ch,
                method,
                properties,
                body
            ):

                try:

                    message = json.loads(body)

                    prompt = message.get("prompt")

                    if not prompt:
                        raise ValueError(
                            "El mensaje no contiene 'prompt'"
                        )

                    logger.info(
                        "Procesando solicitud "
                        "correlation_id=%s",
                        properties.correlation_id
                    )

                    result = ollama_client.generate_response(
                        prompt
                    )

                    response = {
                        "status": "success",
                        "response": result
                    }

                    logger.info(
                        "Respuesta generada correctamente "
                        "correlation_id=%s",
                        properties.correlation_id
                    )

                except Exception as error:

                    logger.exception(
                        "Error procesando solicitud "
                        "correlation_id=%s",
                        properties.correlation_id
                    )

                    response = {
                        "status": "error",
                        "error": str(error)
                    }

                if properties.reply_to:

                    ch.basic_publish(
                        exchange="",
                        routing_key=properties.reply_to,
                        body=json.dumps(response),
                        properties=pika.BasicProperties(
                            correlation_id=properties.correlation_id
                        )
                    )

                ch.basic_ack(
                    delivery_tag=method.delivery_tag
                )

            channel.basic_consume(
                queue=RABBITMQ_QUEUE,
                on_message_callback=process_message,
                auto_ack=False
            )

            channel.start_consuming()

        except AMQPConnectionError:

            logger.exception(
                "RabbitMQ no disponible. "
                "Reintentando en 5 segundos..."
            )

            time.sleep(5)

        except Exception:

            logger.exception(
                "Error inesperado en el worker. "
                "Reintentando en 5 segundos..."
            )

            time.sleep(5)

        finally:

            if connection and connection.is_open:
                connection.close()


if __name__ == "__main__":
    start_worker()