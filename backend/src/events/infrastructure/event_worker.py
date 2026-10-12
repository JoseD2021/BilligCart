from src.events.application.event_registry import EventRegistry
from src.events.infrastructure.rabbitmq_event_bus import RabbitMQEventBus


async def run_event_worker(
    registry: EventRegistry,
    queue_name: str,
) -> None:
    """
    Ejecuta el consumidor de eventos de un servicio.

    Cada servicio aporta su registro de handlers; la conexión,
    el consumo, los ACK y la DLQ son responsabilidad compartida.
    """
    event_bus = RabbitMQEventBus()

    try:
        await event_bus.consume(
            registry=registry,
            queue_name=queue_name,
        )
    finally:
        await event_bus.close()