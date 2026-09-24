"""Rate limiting schemas (admin rule management + daily stats)."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RateLimitScope = Literal["all", "user", "ip"]


class RateLimitRuleOut(BaseModel):
    """One rate limit rule as returned by the admin API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope: RateLimitScope
    limit: int
    window_seconds: int
    action: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RateLimitRuleCreate(BaseModel):
    """Payload for POST /api/v1/admin/rate-limits."""

    scope: RateLimitScope = "all"
    limit: int = Field(..., ge=1, description="Requests allowed per window")
    window_seconds: int = Field(..., ge=1, description="Window length in seconds")
    action: Literal["block"] = "block"
    is_active: bool = True


class RateLimitRuleUpdate(BaseModel):
    """Payload for PATCH /api/v1/admin/rate-limits/{rule_id} — all optional."""

    scope: RateLimitScope | None = None
    limit: int | None = Field(None, ge=1)
    window_seconds: int | None = Field(None, ge=1)
    action: Literal["block"] | None = None
    is_active: bool | None = None


class RateLimitStatsOut(BaseModel):
    """Today's counters from the Redis rate limiter."""

    date: date
    checked: int = 0
    blocked: int = 0
    violations: int = 0
