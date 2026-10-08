from fastapi import FastAPI
from infrastructure.supabase.client import create_supabase_client
from infrastructure.api.v1.error_handlers import register_error_handlers
from infrastructure.api.v1.endpoints.auth import router as auth_router
from infrastructure.api.v1.endpoints.menu import router as menu_router
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.supabase = await create_supabase_client()
    yield
    
prefix = "/api/v1"

app = FastAPI(lifespan=lifespan)
register_error_handlers(app)
app.include_router(auth_router, prefix=prefix)
app.include_router(menu_router, prefix=prefix)