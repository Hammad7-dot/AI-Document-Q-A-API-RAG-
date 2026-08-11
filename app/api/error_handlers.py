"""Global exception handlers mapping AppError subclasses to JSON responses."""
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # exc.errors() can include non-JSON-serializable values in the "input"
        # field (e.g. raw bytes from a malformed body/content-type), which
        # would otherwise crash json.dumps and turn a 400 into an unhandled 500.
        # jsonable_encoder coerces those into safe JSON-compatible representations.
        errors = jsonable_encoder(exc.errors())
        return JSONResponse(status_code=400, content={"detail": "Validation error", "errors": errors})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", path=str(request.url), error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
