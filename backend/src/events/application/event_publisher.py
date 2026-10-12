from abc import ABC, abstractmethod

from src.events.contracts.base_event import BaseEvent


class EventPublisher(ABC):
    """
    Contrato que necesita la aplicación para publicar eventos.

    No conoce RabbitMQ, pika ni aio-pika.
    """

    @abstractmethod
    async def publish(self, event: BaseEvent) -> None:
        raise NotImplementedError