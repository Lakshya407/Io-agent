"""Rate limiting router (admin-only): rules CRUD + daily counters.

The rules here are the source of truth enforced by the ``rate_limit``
dependency (cached briefly in Redis). Endpoint contracts are documented in
docs/API.md.
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, status

from app.core.dependencies import CurrentAdmin, DBSession, RedisClient
from app.schemas.rate_limit import (
    RateLimitRuleCreate,
    RateLimitRuleOut,
    RateLimitRuleUpdate,
    RateLimitStatsOut,
)
from app.services.rate_limit_service import RateLimitService, daily_stats

router = APIRouter(tags=["rate-limits"])


@router.get(
    "/stats",
    response_model=RateLimitStatsOut,
    summary="Today's rate-limit counters",
    operation_id="rate_limits_stats",
)
async def rate_limits_stats(
    admin: CurrentAdmin,
    redis: RedisClient,
) -> RateLimitStatsOut:
    """Requests checked, blocked and violations recorded today (UTC).

    Counters live in Redis and are maintained by the rate limiter itself;
    they reset daily and are best-effort (zeros if Redis has no data).
    """
    today = datetime.now(UTC).date()
    stats = await daily_stats(today.isoformat(), redis)
    return RateLimitStatsOut(
        date=today,
        checked=stats["checked"],
        blocked=stats["blocked"],
        violations=stats["violations"],
    )


@router.get(
    "",
    response_model=list[RateLimitRuleOut],
    summary="List rate limit rules",
    operation_id="rate_limits_list",
)
async def rate_limits_list(
    admin: CurrentAdmin,
    db: DBSession,
) -> list[RateLimitRuleOut]:
    """Every configured rule (admin only)."""
    rules = await RateLimitService(db).list_rules()
    return [RateLimitRuleOut.model_validate(rule) for rule in rules]


@router.post(
    "",
    response_model=RateLimitRuleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a rate limit rule",
    operation_id="rate_limits_create",
)
async def rate_limits_create(
    admin: CurrentAdmin,
    db: DBSession,
    payload: RateLimitRuleCreate,
) -> RateLimitRuleOut:
    """Add a rule; it takes effect on the next request (cache is dropped)."""
    rule = await RateLimitService(db).create_rule(payload)
    return RateLimitRuleOut.model_validate(rule)


@router.patch(
    "/{rule_id}",
    response_model=RateLimitRuleOut,
    summary="Update a rate limit rule",
    operation_id="rate_limits_update",
)
async def rate_limits_update(
    admin: CurrentAdmin,
    db: DBSession,
    rule_id: UUID,
    payload: RateLimitRuleUpdate,
) -> RateLimitRuleOut:
    """Partially update a rule (scope, limit, window, active flag)."""
    rule = await RateLimitService(db).update_rule(rule_id, payload)
    return RateLimitRuleOut.model_validate(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a rate limit rule",
    operation_id="rate_limits_delete",
)
async def rate_limits_delete(
    admin: CurrentAdmin,
    db: DBSession,
    rule_id: UUID,
) -> None:
    """Remove a rule entirely (admin only)."""
    await RateLimitService(db).delete_rule(rule_id)
