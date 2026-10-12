import logging

from src.events.contracts.ai_menu_events import (
    MenuGenerationCompleted,
    MenuGenerationFailed,
    MenuGenerationStarted,
)


logger = logging.getLogger(__name__)


async def on_menu_generation_started(
    event: MenuGenerationStarted,
) -> None:
    logger.info(
        "Generación iniciada: request_id=%s model=%s",
        event.request_id,
        event.model,
    )


async def on_menu_generation_completed(
    event: MenuGenerationCompleted,
) -> None:
    logger.info(
        "Generación completada: request_id=%s model=%s duration_ms=%s",
        event.request_id,
        event.model,
        event.duration_ms,
    )


async def on_menu_generation_failed(
    event: MenuGenerationFailed,
) -> None:
    logger.warning(
        "Generación fallida: request_id=%s model=%s error_type=%s",
        event.request_id,
        event.model,
        event.error_type,
    )