"""Model routing schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoutingRuleOut(BaseModel):
    """One routing rule as returned by the admin routing API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    priority: int
    request_type: str
    primary_model: str
    fallback_model: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RoutingRuleCreate(BaseModel):
    """Payload for POST /api/v1/admin/routing (priority is auto-assigned)."""

    request_type: str = Field(..., min_length=1, max_length=100, examples=["Code"])
    primary_model: str = Field(..., min_length=1, max_length=255)
    fallback_model: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class RoutingRuleUpdate(BaseModel):
    """Payload for PATCH /api/v1/admin/routing/{rule_id} — all optional."""

    request_type: str | None = Field(None, min_length=1, max_length=100)
    primary_model: str | None = Field(None, min_length=1, max_length=255)
    fallback_model: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    priority: int | None = Field(None, ge=1)


class RoutingRuleOrder(BaseModel):
    """Payload for PUT /api/v1/admin/routing/order — full reordering."""

    ids: list[UUID] = Field(..., min_length=1, description="Rule ids, highest priority first")


class RouteResolution(BaseModel):
    """Why a request resolved to a model — useful for debugging/tests."""

    request_type: str
    model: str | None = None
    source: Literal["routing", "default"] = "default"
    rule_id: UUID | None = None
