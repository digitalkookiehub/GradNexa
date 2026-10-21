"""Custom exceptions and handlers. Error body shape: {"detail": "..."}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error carrying an HTTP status code."""

    status_code: int = 400

    def __init__(self, detail: str = "Bad request") -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    """Resource not found."""

    status_code = 404


class ConflictError(AppError):
    """Resource conflict (e.g. duplicate)."""

    status_code = 409


class UnauthorizedError(AppError):
    """Authentication failed."""

    status_code = 401


class ForbiddenError(AppError):
    """Authenticated but not allowed."""

    status_code = 403


class UnprocessableError(AppError):
    """Semantically invalid request content."""

    status_code = 422


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that emit {"detail": "..."} bodies."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=headers)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            {"detail": str(exc.detail)}, status_code=exc.status_code, headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        messages = [
            ".".join(str(p) for p in e["loc"] if p != "body") + ": " + str(e["msg"])
            for e in exc.errors()
        ]
        return JSONResponse({"detail": "; ".join(messages)}, status_code=422)

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse({"detail": "Internal server error"}, status_code=500)
