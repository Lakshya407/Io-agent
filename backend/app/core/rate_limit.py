"""Redis-backed rate limiting.

Implemented as a single FastAPI dependency (per the spec: "middleware/
dependency based rather than duplicated across every endpoint") so any route
can opt in with ``Depends(rate_limit)``.

Limits come from the admin-managed ``rate_limit_rules`` table (cached briefly
in Redis; see ``app.services.rate_limit_service``), falling back to
``RATE_LIMIT_PER_MINUTE`` / ``RATE_LIMIT_PER_HOUR`` settings when the table is
empty or unreachable. Requests are counted per user when authenticated,
otherwise per client IP. Every checked request and every rejection is
recorded in a daily Redis counter the admin Rate Limiting page reads.
"""

import time
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.core.dependencies import DBSession, RedisClient, get_optional_user
from app.core.exceptions import RateLimitException
from app.core.logging import get_logger
from app.models.user import User
from app.services.rate_limit_service import (
    EffectiveRule,
    bump_stats,
    load_effective_rules,
    rule_bucket,
    scope_matches,
)

logger = get_logger(__name__)


async def _hit(
    redis: Redis,
    key: str,
    limit: int,
    window: int,
    *,
    track_stats: bool = False,
) -> None:
    """Increment a sliding-window counter and reject when over the limit.

    With ``track_stats`` the daily counters are updated: ``blocked`` on every
    rejection and ``violations`` once per identity when it first crosses the
    limit (count == limit + 1).
    """
    count = await redis.incr(key)
    if count == 1:
        # Only the first increment sets the expiry.
        await redis.expire(key, window)
    if count > limit:
        if track_stats:
            await bump_stats("blocked", redis=redis)
            if count == limit + 1:
                await bump_stats("violations", redis=redis)
        raise RateLimitException(
            "Too many requests. Please slow down.",
            code="RATE_LIMIT_EXCEEDED",
        )


async def rate_limit(
    request: Request,
    redis: RedisClient,
    db: DBSession,
    current_user: Annotated[User | None, Depends(get_optional_user)],
) -> None:
    """Enforce the active rate-limit rules.

    Identity comes from the authenticated user when available and falls back
    to the client IP for unauthenticated endpoints. Only rules whose scope
    matches the identity (``all`` / ``user`` / ``ip``) are applied. The rules
    are read from a short-lived Redis cache; ``db`` (shared with the route
    via FastAPI's dependency cache) is only touched on a cache miss.
    """
    if current_user is not None:
        identity = f"user:{current_user.id}"
        request_scope = "user"
    else:
        client = request.client
        identity = f"ip:{client.host if client else 'unknown'}"
        request_scope = "ip"

    try:
        await bump_stats("checked", redis=redis)
    except Exception as exc:  # noqa: BLE001 — stats must never block requests
        logger.warning("Rate-limit checked counter failed: %s", exc)

    rules: list[EffectiveRule] = await load_effective_rules(db, redis)
    now = time.time()
    for rule in rules:
        if not scope_matches(rule.scope, request_scope):
            continue
        await _hit(
            redis,
            rule_bucket(rule.id, identity, now, rule.window_seconds),
            rule.limit,
            window=rule.window_seconds,
            track_stats=True,
        )
