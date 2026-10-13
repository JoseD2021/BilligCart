import logging

from src.application.use_cases.persist_generated_menu import (
    PersistGeneratedMenuUseCase,
)
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
    use_case: PersistGeneratedMenuUseCase,
) -> None:
    logger.info(
        "Generación completada: request_id=%s model=%s duration_ms=%s",
        event.request_id,
        event.model,
        event.duration_ms,
    )

    if not event.user_id or not event.response:
        logger.warning(
            "El evento no trae user_id o respuesta; no se guarda el menú. "
            "request_id=%s",
            event.request_id,
        )
        return

    try:
        total = await use_case.execute(event.user_id, event.response)
    except Exception:
        logger.exception(
            "No se pudo guardar el menú generado. request_id=%s user_id=%s",
            event.request_id,
            event.user_id,
        )
        raise

    logger.info(
        "Menú guardado: request_id=%s user_id=%s platos=%s",
        event.request_id,
        event.user_id,
        total,
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
