"""HTTP middleware: request ID propagation and response timing.

- ``RequestIDMiddleware`` preserves a client-supplied ``X-Request-ID`` or
  generates one, then echoes it back in the response headers.
- ``TimingMiddleware`` measures request duration and emits a structured
  log line, e.g. ``GET /api/v1/models -> 42ms``.
"""

import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.logging import get_logger, request_id_ctx, user_id_ctx

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
RESPONSE_TIME_HEADER = "X-Response-Time"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Give every request a unique ID for tracing through logs."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming if incoming else str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            request_id_ctx.reset(token)


class TimingMiddleware(BaseHTTPMiddleware):
    """Measure request duration and log the access line."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "%s %s -> %.0fms (raised)", method, path, duration_ms
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers[RESPONSE_TIME_HEADER] = f"{duration_ms:.0f}ms"
        logger.info(
            "%s %s -> %s %.0fms",
            method,
            path,
            response.status_code,
            duration_ms,
            extra={
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "user_id": user_id_ctx.get(),
            },
        )
        return response


def register_middleware(app: FastAPI) -> None:
    """Register all application middleware in the correct order."""
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)
