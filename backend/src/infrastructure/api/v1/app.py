from fastapi import FastAPI
from src.infrastructure.api.v1.endpoints.routes import health
from src.infrastructure.api.v1.endpoints.ai import ai

def create_app() -> FastAPI:
    app = FastAPI()
    
    app.include_router(health, prefix="/api/v1")
    app.include_router(ai, prefix="/api/v1")
    return app

app = create_app()