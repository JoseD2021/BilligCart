import asyncio
import functools
import logging
import os

from src.application.use_cases.persist_generated_menu import (
    PersistGeneratedMenuUseCase,
)
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
from src.infrastructure.api.v1.dependencies import (
    get_ingrediente_repository,
    get_menu_repository,
    get_plato_ingrediente_repository,
    get_plato_repository,
)
from src.infrastructure.supabase.client import create_supabase_client


logging.basicConfig(level=logging.INFO)


async def main() -> None:
    # Composition root del worker: aquí se construyen las dependencias y se
    # inyectan en los handlers, igual que hace dependencies.py para la API.
    supabase = await create_supabase_client()

    use_case = PersistGeneratedMenuUseCase(
        menu=get_menu_repository(supabase),
        plato=get_plato_repository(supabase),
        ingrediente=get_ingrediente_repository(supabase),
        plato_ingrediente=get_plato_ingrediente_repository(supabase),
    )

    registry = EventRegistry()

    registry.register(
        MenuGenerationStarted,
        on_menu_generation_started,
    )
    registry.register(
        MenuGenerationCompleted,
        functools.partial(
            on_menu_generation_completed,
            use_case=use_case,
        ),
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
