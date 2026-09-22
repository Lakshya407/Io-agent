"""Structured application logging.

Emits one line per request with timestamp, level, request id, method,
endpoint, status code and duration. Secrets (passwords, tokens, API keys)
are never logged.
"""

import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)


class StructuredFormatter(logging.Formatter):
    """Formatter that augments each record with request/user context."""

    def format(self, record: logging.LogRecord) -> str:
        record.request_id = request_id_ctx.get() or "-"
        record.user_id = user_id_ctx.get() or "-"
        record.timestamp = datetime.now(timezone.utc).isoformat()
        return super().format(record)


DEVELOPMENT_FORMAT = (
    "%(timestamp)s | %(levelname)-7s | req=%(request_id)s "
    "user=%(user_id)s | %(name)s | %(message)s"
)
PRODUCTION_FORMAT = (
    '{"timestamp":"%(timestamp)s","level":"%(levelname)s",'
    '"request_id":"%(request_id)s","user_id":"%(user_id)s",'
    '"logger":"%(name)s","message":"%(message)s"}'
)


def setup_logging(debug: bool = False, is_production: bool = False) -> None:
    """Configure the root logger once at startup."""
    log_format = PRODUCTION_FORMAT if is_production else DEVELOPMENT_FORMAT
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter(log_format))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Quiet noisy third-party loggers.
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger whose records carry request context."""
    return logging.getLogger(name)
