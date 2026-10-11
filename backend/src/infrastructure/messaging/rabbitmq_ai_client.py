import json
import os
import time
import uuid

import pika

from src.domain.repositories.ai_client_interface import AIClientInterface


class RabbitMQAIClient(AIClientInterface):

    def __init__(self):
        self.host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.user = os.getenv("RABBITMQ_USER")
        self.password = os.getenv("RABBITMQ_PASSWORD")
        self.queue_name = os.getenv(
            "RABBITMQ_QUEUE",
            "ai_requests"
        )

    def generate_response(self, prompt: str) -> str:

        credentials = pika.PlainCredentials(
            self.user,
            self.password
        )

        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials,
            heartbeat=60,
            connection_attempts=5,
            retry_delay=2
        )

        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        channel.queue_declare(
            queue=self.queue_name,
            durable=True
        )

        callback_queue = channel.queue_declare(
            queue="",
            exclusive=True,
            auto_delete=True
        )

        reply_queue = callback_queue.method.queue

        correlation_id = str(uuid.uuid4())

        response = {}

        def on_response(ch, method, properties, body):

            if properties.correlation_id == correlation_id:
                response["data"] = json.loads(body)

        channel.basic_consume(
            queue=reply_queue,
            on_message_callback=on_response,
            auto_ack=True
        )

        message = {
            "prompt": prompt
        }

        channel.basic_publish(
            exchange="",
            routing_key=self.queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                reply_to=reply_queue,
                correlation_id=correlation_id,
                delivery_mode=2
            )
        )

        timeout = 120
        start_time = time.monotonic()

        while "data" not in response:

            if time.monotonic() - start_time > timeout:
                connection.close()
                raise TimeoutError(
                    "No se recibió respuesta del AI Worker"
                )

            connection.process_data_events(
                time_limit=1
            )

        connection.close()

        data = response["data"]

        if data.get("status") == "error":
            raise RuntimeError(
                data.get(
                    "error",
                    "Error procesando solicitud de IA"
                )
            )

        return data["response"]