"""Global error handling.

Maps domain and infrastructure errors to consistent HTTP responses. Domain code
stays framework-agnostic; translation to HTTP happens here.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.shared.exceptions import (
    ConflictError,
    DomainError,
    EntityNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Domain error -> HTTP status mapping.
_STATUS_MAP: dict[type[DomainError], int] = {
    EntityNotFoundError: status.HTTP_404_NOT_FOUND,
    ValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ConflictError: status.HTTP_409_CONFLICT,
    ServiceUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _error_body(error: str, detail: str | None = None) -> dict[str, str | None]:
    return {"error": error, "detail": detail}


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the app."""

    @app.exception_handler(DomainError)
    async def _handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        http_status = _STATUS_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST)
        logger.warning("domain_error", error=type(exc).__name__, message=exc.message)
        return JSONResponse(
            status_code=http_status,
            content=_error_body(type(exc).__name__, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body("ValidationError", str(exc.errors())),
        )

    @app.exception_handler(NotImplementedError)
    async def _handle_not_implemented(_: Request, exc: NotImplementedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content=_error_body("NotImplemented", "This feature is not implemented."),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_error", error=type(exc).__name__, message=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("InternalServerError", "An unexpected error occurred."),
        )
