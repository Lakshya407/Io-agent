"""Asynchronous Redis connection layer.

Redis is used only for short-lived, non-primary state: rate limiting,
caching and counters. It is never used as the primary database.
"""

from collections.abc import AsyncGenerator

from redis.asyncio import Redis, from_url

from app.core.config import settings

redis_client: Redis = from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
    max_connections=20,
    health_check_interval=30,
)


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency that yields the shared async Redis client."""
    try:
        yield redis_client
    finally:
        # Connections are returned to the pool automatically.
        pass


async def close_redis() -> None:
    """Close the Redis connection pool (used on application shutdown)."""
    await redis_client.aclose()
