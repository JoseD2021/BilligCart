from fastapi import APIRouter

health = APIRouter()

@health.get("/health")
def health_check():
    return {"status": "ok", "message": "API funcionando correctamente"}