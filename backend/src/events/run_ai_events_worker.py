import asyncio
import logging
import os

from src.events.application.ai_event_handlers import (
    on_menu_generation_completed,
    on_menu_generation_failed,
    on_menu_generation_started,
)
from src.events.application.event_registry import EventRegistry
from src.events.contracts.ai_menu_events import (
    MenuGenerationCompleted,
    MenuGenerationFailed,
    MenuGenerationStarted,
)
from src.events.infrastructure.event_worker import run_event_worker


logging.basicConfig(level=logging.INFO)


async def main() -> None:
    registry = EventRegistry()

    registry.register(
        MenuGenerationStarted,
        on_menu_generation_started,
    )
    registry.register(
        MenuGenerationCompleted,
        on_menu_generation_completed,
    )
    registry.register(
        MenuGenerationFailed,
        on_menu_generation_failed,
    )

    await run_event_worker(
        registry=registry,
        queue_name=os.getenv(
            "RABBITMQ_EVENT_QUEUE",
            "application_events",
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())