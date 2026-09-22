"""Tool configuration schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.tool import ToolType


class ToolOut(BaseModel):
    """Public tool configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    type: ToolType
    configuration: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ToolCreate(BaseModel):
    """Payload for POST /api/v1/admin/tools."""

    name: str = Field(..., min_length=1, max_length=255, examples=["web-search"])
    description: str = Field(..., min_length=1)
    type: ToolType = ToolType.UTILITY
    configuration: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class ToolUpdate(BaseModel):
    """Payload for PUT /api/v1/admin/tools/{tool_id}."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    type: ToolType | None = None
    configuration: dict[str, Any] | None = None


class ToolStatusUpdate(BaseModel):
    """Payload for PATCH /api/v1/admin/tools/{tool_id}/status."""

    is_active: bool
