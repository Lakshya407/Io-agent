"""Usage schemas (allowance, personal views, admin analytics)."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UsageOut(BaseModel):
    """Allowance summary for a single user.

    ``tokens_remaining`` / ``requests_remaining`` / ``is_allowed`` are computed
    properties on the ORM model and are read through ``from_attributes``.
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    monthly_token_limit: int
    monthly_request_limit: int
    daily_token_limit: int | None = None
    daily_request_limit: int | None = None
    is_enabled: bool = True
    tokens_used: int
    requests_used: int
    tokens_remaining: int
    requests_remaining: int
    is_allowed: bool
    reset_at: datetime


class AllowanceUpdate(BaseModel):
    """Payload for PATCH /api/v1/admin/users/{user_id}/allowance."""

    monthly_token_limit: int | None = Field(None, ge=0)
    monthly_request_limit: int | None = Field(None, ge=0)
    daily_token_limit: int | None = Field(None, ge=0)
    daily_request_limit: int | None = Field(None, ge=0)
    is_enabled: bool | None = None
    reset_at: datetime | None = None


class UsageHistoryItem(BaseModel):
    """One aggregated row of usage history (per day)."""

    period: date
    requests: int
    tokens: int


class UsageMeOut(BaseModel):
    """Full personal usage view — GET /api/v1/usage/me.

    Only ever contains the authenticated user's own numbers.
    """

    # Today (UTC day, from usage_records with a Redis fast path).
    tokens_today: int
    requests_today: int
    tokens_remaining_today: int | None = None
    requests_remaining_today: int | None = None
    # Current allowance period (monthly counters on usage_allowances).
    tokens_this_month: int
    requests_this_month: int
    tokens_remaining: int
    requests_remaining: int
    # Configuration.
    monthly_token_limit: int
    monthly_request_limit: int
    daily_token_limit: int | None = None
    daily_request_limit: int | None = None
    is_enabled: bool
    is_allowed: bool
    reset_at: datetime
    # Model the chat UI will use when the request names none.
    current_model: str | None = None


class UsageSummaryOut(BaseModel):
    """Compact usage summary — GET /api/v1/usage/summary."""

    tokens_today: int
    requests_today: int
    tokens_this_month: int
    requests_this_month: int
    tokens_remaining: int
    requests_remaining: int
    current_model: str | None = None


class AdminUsageRow(BaseModel):
    """Allowance of a single user, joined with their identity (admin views)."""

    user_id: UUID
    email: str
    name: str
    role: str
    monthly_token_limit: int
    monthly_request_limit: int
    tokens_used: int
    requests_used: int
    tokens_remaining: int
    requests_remaining: int
    reset_at: datetime


# --- Admin analytics (aggregated over usage_records) ---------------------


class AdminUsageSummary(BaseModel):
    """Platform totals for the filtered period — GET /admin/usage/summary."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    cancelled_requests: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    active_users: int
    average_response_time_ms: float | None = None


class AdminModelUsageRow(BaseModel):
    """Usage aggregated per model — GET /admin/usage/models."""

    model: str
    provider: str | None = None
    requests: int
    successful_requests: int
    failed_requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    average_response_time_ms: float | None = None


class AdminUserUsageRow(BaseModel):
    """Usage aggregated per user — GET /admin/usage/users."""

    user_id: UUID
    email: str
    name: str
    requests: int
    successful_requests: int
    failed_requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    average_response_time_ms: float | None = None


class UsageTimelinePoint(BaseModel):
    """One day of usage — GET /admin/usage/timeline."""

    period: date
    requests: int
    failed_requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    average_response_time_ms: float | None = None
