"""Standardized error envelope: { "error": { "code", "message", "detail" } }."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base class for application-level errors that map to a JSON envelope."""

    code: str = "internal_error"
    status_code: int = 500
    message: str = "An internal error occurred."

    def __init__(self, message: str | None = None, detail: dict[str, Any] | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.detail = detail or {}


class UnauthorizedError(AppError):
    code = "unauthorized"
    status_code = 401
    message = "Authentication required."


class ForbiddenError(AppError):
    code = "forbidden"
    status_code = 403
    message = "You do not have access to this resource."


class NotFoundError(AppError):
    code = "not_found"
    status_code = 404
    message = "Resource not found."


def _envelope(code: str, message: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "detail": detail or {}}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_req: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.detail),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_req: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope("http_error", str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_req: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope("validation_error", "Invalid request payload.", {"errors": exc.errors()}),
        )
