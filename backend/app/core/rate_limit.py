"""Redis-backed rate limiting.

Implemented as a single FastAPI dependency (per the spec: "middleware/
dependency based rather than duplicated across every endpoint") so any route
can opt in with ``Depends(rate_limit)``.

Limits are configured through ``RATE_LIMIT_PER_MINUTE`` and
``RATE_LIMIT_PER_HOUR`` and counted per user when authenticated, otherwise per
client IP.
"""

import time
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.core.config import settings
from app.core.dependencies import RedisClient, get_optional_user
from app.core.exceptions import RateLimitException
from app.models.user import User


async def _hit(redis: Redis, key: str, limit: int, window: int) -> None:
    """Increment a sliding-window counter and reject when over the limit."""
    count = await redis.incr(key)
    if count == 1:
        # Only the first increment sets the expiry.
        await redis.expire(key, window)
    if count > limit:
        raise RateLimitException(
            "Too many requests. Please slow down.",
            code="RATE_LIMIT_EXCEEDED",
        )


async def rate_limit(
    request: Request,
    redis: RedisClient,
    current_user: Annotated[User | None, Depends(get_optional_user)],
) -> None:
    """Enforce per-minute and per-hour request limits.

    Identity comes from the authenticated user when available and falls back
    to the client IP for unauthenticated endpoints.
    """
    if current_user is not None:
        identity = f"user:{current_user.id}"
    else:
        client = request.client
        identity = f"ip:{client.host if client else 'unknown'}"

    now = time.time()
    minute_bucket = int(now // 60)
    hour_bucket = int(now // 3600)

    await _hit(
        redis,
        f"ratelimit:{identity}:minute:{minute_bucket}",
        settings.rate_limit_per_minute,
        window=60,
    )
    await _hit(
        redis,
        f"ratelimit:{identity}:hour:{hour_bucket}",
        settings.rate_limit_per_hour,
        window=3600,
    )
