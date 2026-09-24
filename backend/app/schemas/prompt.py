"""Prompt management schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PromptStatus = Literal["active", "draft", "inactive"]


class PromptOut(BaseModel):
    """One prompt as returned by the admin prompts API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    purpose: str
    model: str | None = None
    version: int
    status: PromptStatus
    content: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class PromptCreate(BaseModel):
    """Payload for POST /api/v1/prompts."""

    name: str = Field(..., min_length=1, max_length=255, examples=["Default Assistant"])
    purpose: str = Field(default="", max_length=255, examples=["General agent behavior"])
    model: str | None = Field(default=None, max_length=255)
    version: int = Field(default=1, ge=1)
    status: PromptStatus = "draft"
    content: str = Field(..., min_length=1, examples=["You are a helpful assistant."])
    is_default: bool = False


class PromptUpdate(BaseModel):
    """Payload for PATCH /api/v1/prompts/{prompt_id} — all fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    purpose: str | None = Field(None, max_length=255)
    model: str | None = None
    version: int | None = Field(None, ge=1)
    status: PromptStatus | None = None
    content: str | None = Field(None, min_length=1)
    is_default: bool | None = None
