"""Centralized exception definitions and consistent error responses."""

from typing import Any
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, request_id_ctx

logger = get_logger(__name__)


class AppException(Exception):
    """Base exception for all expected application errors."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class UnauthorizedException(AppException):
    code = "UNAUTHORIZED"
    status_code = 401
    message = "Authentication is required."


class ForbiddenException(AppException):
    code = "FORBIDDEN"
    status_code = 403
    message = "You do not have permission to perform this action."


class NotFoundException(AppException):
    code = "NOT_FOUND"
    status_code = 404
    message = "Resource not found."


class ConflictException(AppException):
    code = "CONFLICT"
    status_code = 409
    message = "Resource already exists."


class ValidationException(AppException):
    code = "VALIDATION_ERROR"
    status_code = 422
    message = "Request validation failed."


class UsageLimitExceededException(AppException):
    code = "USAGE_LIMIT_EXCEEDED"
    status_code = 429
    message = "Monthly usage allowance exceeded."


class RateLimitException(AppException):
    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429
    message = "Too many requests."


class ServiceUnavailableException(AppException):
    code = "SERVICE_UNAVAILABLE"
    status_code = 503
    message = "AI service is currently unavailable. Please try again."


def _error_response(
    status_code: int,
    code: str,
    message: str,
    request: Request,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Build the single error envelope used across the whole API."""
    body: dict[str, Any] = {
        "success": False,
        "error": {"code": code, "message": message},
        "request_id": request_id_ctx.get() or request.headers.get(
            "X-Request-ID", "-"
        ),
    }
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """Register every exception handler on the application."""

    @app.exception_handler(AppException)
    async def handle_app_exception(
        request: Request, exc: AppException
    ) -> JSONResponse:
        if exc.status_code >= 500:
            logger.exception("Unhandled application error: %s", exc.code)
        return _error_response(
            exc.status_code, exc.code, exc.message, request, exc.details
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            422,
            ValidationException.code,
            "Request validation failed.",
            request,
            details={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # Never expose internal stack traces to clients.
        logger.exception("Unexpected error: %s", type(exc).__name__)
        return _error_response(
            500,
            AppException.code,
            "An unexpected error occurred.",
            request,
        )


def not_found(resource: str, resource_id: str | UUID) -> NotFoundException:
    """Helper to build a consistent 404 for a missing resource."""
    return NotFoundException(f"{resource} not found: {resource_id}")
