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
from src.events.application.payment_event_handlers import (
    on_payment_requested,
    on_payment_succeeded,
)
from src.events.contracts.ai_menu_events import (
    MenuGenerationCompleted,
    MenuGenerationFailed,
    MenuGenerationStarted,
)
from src.events.contracts.gps_events import LocationRecorded
from src.events.contracts.payment_events import PaymentRequested, PaymentSucceeded
from src.events.infrastructure.event_worker import run_event_worker
from src.infrastructure.api.v1.dependencies import (
    get_ingrediente_repository,
    get_menu_repository,
    get_plato_ingrediente_repository,
    get_plato_repository,
)
from src.infrastructure.payments.config import payment_store
from src.infrastructure.payments.supabase_projection import SupabasePaymentProjection
from src.infrastructure.supabase.client import create_supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def on_location_recorded(event: LocationRecorded, supabase) -> None:
    payload = {
        "repartidor_id": event.courier_id,
        "lat": event.lat,
        "lng": event.lng,
        "accuracy": event.accuracy,
        "heading": event.heading,
        "speed": event.speed,
        "updated_at": event.occurred_at.isoformat(),
    }
    await supabase.table("Ubicacion").upsert(payload, on_conflict="repartidor_id").execute()
    logger.info("Ubicación persistida para repartidor=%s pedido=%s", event.courier_id, event.order_id)


async def main() -> None:
    supabase = await create_supabase_client()

    use_case = PersistGeneratedMenuUseCase(
        menu=get_menu_repository(supabase),
        plato=get_plato_repository(supabase),
        ingrediente=get_ingrediente_repository(supabase),
        plato_ingrediente=get_plato_ingrediente_repository(supabase),
    )

    registry = EventRegistry()
    registry.register(MenuGenerationStarted, on_menu_generation_started)
    registry.register(MenuGenerationCompleted, functools.partial(on_menu_generation_completed, use_case=use_case))
    registry.register(MenuGenerationFailed, on_menu_generation_failed)
    registry.register(LocationRecorded, functools.partial(on_location_recorded, supabase=supabase))
    projection = SupabasePaymentProjection(payment_store(), supabase)
    registry.register(PaymentRequested, on_payment_requested)
    registry.register(PaymentSucceeded, functools.partial(on_payment_succeeded, projection=projection))

    await run_event_worker(
        registry=registry,
        queue_name=os.getenv("RABBITMQ_EVENT_QUEUE", "application_events"),
    )


if __name__ == "__main__":
    asyncio.run(main())
