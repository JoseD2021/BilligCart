from fastapi import FastAPI
from infrastructure.api.v1.routes import router

def create_app() -> FastAPI:
    app = FastAPI()
    
    app.include_router(router, prefix="/api/v1")
    return app

app = create_app()