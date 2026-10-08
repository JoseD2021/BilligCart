from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from domain.errors import (
    DomainError, EmailAlreadyRegistered, InvalidCredentials, InvalidEmail, UserNotFound, WeakPassword,
)

STATUS_BY_ERROR = {
    EmailAlreadyRegistered: 409,
    InvalidCredentials: 401,
    UserNotFound: 404,
    InvalidEmail: 422,
    WeakPassword: 422,
}

def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError):
        status = STATUS_BY_ERROR.get(type(exc), 400)
        return JSONResponse(
            status_code=status,
            content={"error": type(exc).__name__, "message": exc.message},
        )
        
    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": "InternalError", "message": "Hubo un error inesperado en el servidor."},
        )