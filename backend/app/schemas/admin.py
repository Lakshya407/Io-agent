"""Admin schemas (dashboard aggregates + audit log views)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.audit_log import AuditAction


class DashboardStats(BaseModel):
    """Aggregated platform statistics returned by GET /api/v1/admin/dashboard."""

    total_users: int = Field(..., examples=[120])
    active_users: int = Field(..., examples=[87])
    total_requests: int = Field(..., examples=[45230])
    total_tokens: int = Field(..., examples=[1289340])
    active_models: int = Field(..., examples=[6])
    active_tools: int = Field(..., examples=[8])


class AuditLogOut(BaseModel):
    """An immutable audit event."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    user_id: UUID | None = None
    action: AuditAction
    resource_type: str
    resource_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    # The ORM attribute is ``metadata_`` (mapped to the ``metadata`` column);
    # validate from that attribute but expose it as ``metadata`` in the API.
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    created_at: datetime
