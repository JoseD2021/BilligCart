import logging
from time import perf_counter
from uuid import uuid4

from fastapi.responses import JSONResponse

logger = logging.getLogger("billigcart.api")


def register_request_logging(app):
    @app.middleware("http")
    async def log_request(request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed request_id=%s method=%s path=%s",
                             request_id, request.method, request.url.path)
            response = JSONResponse(status_code=500, content={
                "error": "InternalError", "message": "Hubo un error inesperado en el servidor.",
            })
        response.headers["X-Request-ID"] = request_id
        logger.info("request_completed request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
                    request_id, request.method, request.url.path, response.status_code,
                    (perf_counter() - started) * 1000)
        return response
