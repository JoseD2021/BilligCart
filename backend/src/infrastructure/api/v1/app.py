from fastapi import FastAPI
import logging
import os
from src.infrastructure.api.v1.endpoints.routes import health
from src.infrastructure.api.v1.endpoints.ai import ai

from src.infrastructure.supabase.client import create_supabase_client
from src.infrastructure.api.v1.error_handlers import register_error_handlers
from src.infrastructure.api.v1.endpoints.auth import router as auth_router
from src.infrastructure.api.v1.endpoints.menu import router as menu_router
from src.infrastructure.api.v1.endpoints.plato import router as plato_router
from src.infrastructure.api.v1.endpoints.ingrediente import router as ingrediente_router
from src.infrastructure.api.v1.endpoints.plato_ingrediente import router as plato_ingrediente_router
from src.infrastructure.api.v1.endpoints.preferencias import router as preferencias_router
from src.infrastructure.api.v1.endpoints.compras import router as compras_router
from src.infrastructure.api.v1.request_logging import register_request_logging
from src.infrastructure.api.v1.endpoints.payments import router as payments_router

from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.supabase = await create_supabase_client()
    # Los métodos de login pueden cambiar la sesión interna del SDK. Separar
    # Auth evita que sustituyan la identidad del cliente de persistencia.
    app.state.auth_supabase = await create_supabase_client()
    yield

prefix = "/v1"

def create_app() -> FastAPI:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app = FastAPI(lifespan=lifespan, root_path="/api")
    register_error_handlers(app)
    register_request_logging(app)

    app.include_router(health, prefix=prefix)
    app.include_router(ai, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(menu_router, prefix=prefix)
    app.include_router(plato_router, prefix=prefix)
    app.include_router(ingrediente_router, prefix=prefix)
    app.include_router(plato_ingrediente_router, prefix=prefix)
    app.include_router(preferencias_router, prefix=prefix)
    app.include_router(compras_router, prefix=prefix)
    app.include_router(payments_router, prefix=prefix)
    return app

app = create_app()
