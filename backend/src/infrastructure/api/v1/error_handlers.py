from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from postgrest import APIError
import logging
from src.domain.errors import AccessDenied, ResourceNotFound, IngredienteNotFound, OrderNotReady, MenuGenerationError
from src.domain.errors import (
    DomainError, EmailAlreadyRegistered, IngredienteRecentlyUpdated, InvalidCredentials, InvalidEmail, InvalidRequestBodyError, UserNotFound, WeakPassword,
)

STATUS_BY_ERROR = {
    EmailAlreadyRegistered: 409,
    InvalidCredentials: 401,
    UserNotFound: 404,
    InvalidEmail: 422,
    WeakPassword: 422,
    InvalidRequestBodyError: 400,
    IngredienteRecentlyUpdated: 429,
    AccessDenied: 403,
    ResourceNotFound: 404,
    IngredienteNotFound: 404,
    OrderNotReady: 409,
    MenuGenerationError: 502,
}

logger = logging.getLogger("billigcart.api")

def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError):
        status = STATUS_BY_ERROR.get(type(exc), 400)
        logger.warning("domain_error request_id=%s error=%s status=%s",
                       getattr(request.state, "request_id", ""), type(exc).__name__, status)
        return JSONResponse(
            status_code=status,
            content={"error": type(exc).__name__, "message": exc.message},
        )

    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError):
        logger.exception("database_error request_id=%s", getattr(request.state, "request_id", ""))
        return JSONResponse(
            status_code=500,
            content={"error": "PersistenceError", "message": "No se pudo completar la operación de datos."},
        )

    @app.exception_handler(TimeoutError)
    async def handle_timeout(request: Request, exc: TimeoutError):
        logger.warning("upstream_timeout request_id=%s", getattr(request.state, "request_id", ""))
        return JSONResponse(status_code=504, content={"error": "AITimeout", "message": "La IA tardó demasiado en responder."})

    @app.exception_handler(ConnectionError)
    async def handle_connection(request: Request, exc: ConnectionError):
        logger.warning("upstream_unavailable request_id=%s", getattr(request.state, "request_id", ""))
        return JSONResponse(status_code=503, content={"error": "AIUnavailable", "message": "El servicio de IA no está disponible."})

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("unexpected_error request_id=%s", getattr(request.state, "request_id", ""))
        return JSONResponse(
            status_code=500,
            content={"error": "InternalError", "message": "Hubo un error inesperado en el servidor."},
        )
