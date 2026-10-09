from fastapi import FastAPI
from src.infrastructure.api.v1.endpoints.routes import health
from src.infrastructure.api.v1.endpoints.ai import ai

from src.infrastructure.supabase.client import create_supabase_client
from src.infrastructure.api.v1.error_handlers import register_error_handlers
from src.infrastructure.api.v1.endpoints.auth import router as auth_router
from src.infrastructure.api.v1.endpoints.menu import router as menu_router
from src.infrastructure.api.v1.endpoints.plato import router as plato_router
from src.infrastructure.api.v1.endpoints.ingrediente import router as ingrediente_router
from src.infrastructure.api.v1.endpoints.plato_ingrediente import router as plato_ingrediente_router

from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.supabase = await create_supabase_client()
    yield

prefix = "/api/v1"

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    register_error_handlers(app)
    
    app.include_router(health, prefix=prefix)
    app.include_router(ai, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(menu_router, prefix=prefix)
    app.include_router(plato_router, prefix=prefix)
    app.include_router(ingrediente_router, prefix=prefix)
    app.include_router(plato_ingrediente_router, prefix=prefix)
    return app

app = create_app()