from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from src.events.infrastructure.rabbitmq_event_bus import RabbitMQEventBus
from src.infrastructure.gps.bootstrap import build_gps_container
from src.infrastructure.gps.config import GpsSettings
from src.infrastructure.gps.security.supabase_order_access import SupabaseOrderAccess
from src.infrastructure.gps.web.routes import router as gps_router
from src.infrastructure.supabase.auth_service import SupabaseAuthService
from src.infrastructure.supabase.client import create_supabase_client

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    supabase = await create_supabase_client()
    role_supabase = await create_supabase_client()
    bus = RabbitMQEventBus()
    await bus.connect()  # conectar al arrancar evita que dos publicaciones simultáneas abran dos conexiones

    app.state.supabase = supabase
    app.state.gps = build_gps_container(
        auth=SupabaseAuthService(supabase, role_client=role_supabase),
        access=SupabaseOrderAccess(supabase),
        events=bus,
        settings=GpsSettings.from_env(),
    )
    try:
        yield
    finally:
        await app.state.gps.background.drain()  # termina de publicar lo pendiente
        await bus.close()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)
    app.include_router(gps_router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
