"""Rate limit service: admin CRUD, effective-rule loading, daily stats.

Effective rules (what the FastAPI ``rate_limit`` dependency actually enforces)
resolve in this order:

1. a short-lived Redis cache of the active DB rows,
2. the ``rate_limit_rules`` table (admin-managed source of truth),
3. built-in ``RATE_LIMIT_PER_MINUTE`` / ``RATE_LIMIT_PER_HOUR`` settings —
   used when the table is empty or unreachable, so upgrading from the
   settings-only setup never changes behaviour.

Admin mutations invalidate the Redis cache so edits apply within one request.

Daily counters (``checked`` / ``blocked`` / ``violations``) are maintained by
the rate limiter in a Redis hash keyed by UTC date; the admin stats endpoint
only reads them.
"""

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import redis_client
from app.models.rate_limit_rule import RateLimitRule
from app.schemas.rate_limit import (
    RateLimitRuleCreate,
    RateLimitRuleUpdate,
)

logger = get_logger(__name__)

# Redis cache holding the serialized active rules, invalidated on mutation.
RULES_CACHE_KEY = "ratelimit:rules:v1"
RULES_CACHE_TTL = 30

# Redis hash of daily counters: ratelimit:stats:{YYYY-MM-DD}
STATS_PREFIX = "ratelimit:stats:"
STATS_FIELDS = ("checked", "blocked", "violations")


@dataclass(frozen=True, slots=True)
class EffectiveRule:
    """A rule as seen by the rate-limit dependency (DB or settings)."""

    id: str
    scope: str
    limit: int
    window_seconds: int


def scope_matches(rule_scope: str, request_scope: str) -> bool:
    """``all`` applies everywhere; ``user``/``ip`` only to their identity."""
    return rule_scope == "all" or rule_scope == request_scope


def rule_bucket(rule_id: str, identity: str, now: float, window: int) -> str:
    """Sliding-window counter key: one bucket per rule window."""
    return f"ratelimit:{identity}:{rule_id}:{int(now // window)}"


def stats_key(day: str | None = None) -> str:
    """Redis key for one day's counters (default: today, UTC)."""
    return STATS_PREFIX + (day or datetime.now(UTC).date().isoformat())


def _settings_rules() -> list[EffectiveRule]:
    """Fallback mirroring the pre-Phase-10 behaviour exactly."""
    return [
        EffectiveRule(
            id="settings:minute",
            scope="all",
            limit=settings.rate_limit_per_minute,
            window_seconds=60,
        ),
        EffectiveRule(
            id="settings:hour",
            scope="all",
            limit=settings.rate_limit_per_hour,
            window_seconds=3600,
        ),
    ]


def _encode(rules: Iterable[EffectiveRule]) -> str:
    return json.dumps([asdict(rule) for rule in rules])


def _decode(raw: str | bytes) -> list[EffectiveRule]:
    data = json.loads(raw)
    return [EffectiveRule(**item) for item in data]


async def load_effective_rules(
    db: AsyncSession | None,
    redis: Redis | None,
    *,
    use_cache: bool = True,
) -> list[EffectiveRule]:
    """Active rules for the limiter: cache → DB → settings fallback."""
    if use_cache and redis is not None:
        try:
            cached = await redis.get(RULES_CACHE_KEY)
            if cached:
                return _decode(cached)
        except Exception as exc:  # noqa: BLE001 — Redis problems are never fatal
            logger.warning("Rate-limit rules cache read failed: %s", exc)

    if db is not None:
        try:
            result = await db.execute(
                select(RateLimitRule).where(RateLimitRule.is_active.is_(True))
            )
            rows = list(result.scalars().all())
            if rows:
                rules = [
                    EffectiveRule(
                        id=str(row.id),
                        scope=row.scope,
                        limit=row.limit,
                        window_seconds=row.window_seconds,
                    )
                    for row in rows
                ]
                if redis is not None:
                    try:
                        await redis.set(
                            RULES_CACHE_KEY, _encode(rules), ex=RULES_CACHE_TTL
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Rate-limit rules cache write failed: %s", exc)
                return rules
            # Empty table → fall through to settings (upgraded installs).
        except Exception as exc:  # noqa: BLE001 — never break requests over config
            logger.warning("Rate-limit rules load from DB failed: %s", exc)

    return _settings_rules()


async def clear_rules_cache(redis: Redis | None = None) -> None:
    """Drop the cached rules so the next request re-reads the DB."""
    client = redis or redis_client
    try:
        await client.delete(RULES_CACHE_KEY)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Rate-limit rules cache invalidation failed: %s", exc)


async def bump_stats(
    field: str,
    *,
    amount: int = 1,
    day: str | None = None,
    redis: Redis | None = None,
) -> None:
    """Best-effort increment of a daily counter (never raises)."""
    if field not in STATS_FIELDS:
        return
    try:
        client = redis or redis_client
        key = stats_key(day)
        value = await client.hincrby(key, field, amount)
        if value == amount:  # first write of the day → set the TTL
            await client.expire(key, 60 * 60 * 24 * 7)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Rate-limit stat increment failed (%s): %s", field, exc)


async def daily_stats(
    day: str | None = None, redis: Redis | None = None
) -> dict[str, int]:
    """Read today's counters from Redis (zeros when never touched)."""
    out = {field: 0 for field in STATS_FIELDS}
    try:
        client = redis or redis_client
        raw = await client.hgetall(stats_key(day))
        for field_key, value in (raw or {}).items():
            field = field_key.decode() if isinstance(field_key, bytes) else field_key
            if field in out:
                out[field] = int(value)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Rate-limit stats read failed: %s", exc)
    return out


class RateLimitService:
    """Admin CRUD over the ``rate_limit_rules`` table."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_rules(self) -> list[RateLimitRule]:
        """All rules (any status), shortest window first for display."""
        result = await self.db.execute(
            select(RateLimitRule).order_by(
                RateLimitRule.window_seconds.asc(), RateLimitRule.limit.asc()
            )
        )
        return list(result.scalars().all())

    async def get_rule(self, rule_id) -> RateLimitRule:
        """One rule or a 404."""
        result = await self.db.execute(
            select(RateLimitRule).where(RateLimitRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            from app.core.exceptions import not_found

            raise not_found("Rate limit rule", rule_id)
        return rule

    async def create_rule(self, data: RateLimitRuleCreate) -> RateLimitRule:
        """Add a new rule (takes effect after cache invalidation)."""
        rule = RateLimitRule(**data.model_dump())
        self.db.add(rule)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(rule)
        await clear_rules_cache()
        return rule

    async def update_rule(
        self, rule_id, data: RateLimitRuleUpdate
    ) -> RateLimitRule:
        """Partially update a rule."""
        rule = await self.get_rule(rule_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(rule)
        await clear_rules_cache()
        return rule

    async def delete_rule(self, rule_id) -> None:
        """Remove a rule entirely."""
        rule = await self.get_rule(rule_id)
        await self.db.delete(rule)
        await self.db.commit()
        await clear_rules_cache()

    async def count(self) -> int:
        """Total rule rows (used to decide whether settings are active)."""
        return int(await self.db.scalar(select(func.count()).select_from(RateLimitRule)) or 0)
