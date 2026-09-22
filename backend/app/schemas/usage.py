"""Usage allowance schemas."""

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
    reset_at: datetime | None = None


class UsageHistoryItem(BaseModel):
    """One aggregated row of usage history (per day)."""

    period: date
    requests: int
    tokens: int


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
