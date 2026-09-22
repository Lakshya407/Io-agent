"""Health check endpoints.

``GET /health`` is intentionally lightweight (no I/O) for liveness probes.
``GET /health/ready`` verifies that PostgreSQL and Redis are reachable and
returns a degraded status (HTTP 503) when a dependency is down.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.logging import get_logger
from app.core.redis import redis_client
from app.database.connection import engine
from app.llm.ollama import OllamaProvider

router = APIRouter(prefix="/health", tags=["health"])
logger = get_logger(__name__)


@router.get("", summary="Liveness probe", operation_id="health")
async def health() -> dict[str, str]:
    """Lightweight liveness check — always returns ok if the process is up."""
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe", operation_id="health_ready")
async def health_ready() -> JSONResponse:
    """Readiness check that pings PostgreSQL and Redis."""
    checks: dict[str, str] = {}
    http_status = status.HTTP_200_OK

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001 - readiness must never raise
        checks["postgres"] = f"error: {type(exc).__name__}"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.error("PostgreSQL readiness check failed: %s", exc)

    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001 - readiness must never raise
        checks["redis"] = f"error: {type(exc).__name__}"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.error("Redis readiness check failed: %s", exc)

    overall = "ok" if http_status == status.HTTP_200_OK else "degraded"
    return JSONResponse(
        status_code=http_status,
        content={"status": overall, "checks": checks},
    )


@router.get("/llm", summary="LLM provider probe", operation_id="health_llm")
async def health_llm() -> JSONResponse:
    """Check that the backend can reach the configured LLM provider.

    Deliberately separate from ``/health/ready``: an unavailable LLM degrades
    chat but must never take the whole service (or its container healthcheck)
    down. Ollama is contacted best-effort; a failure still returns a payload.
    """
    result = await OllamaProvider().health_check()
    http_status = (
        status.HTTP_200_OK
        if result.get("status") == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(status_code=http_status, content=result)
