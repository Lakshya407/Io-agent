"""Model configuration schemas.

Provider/type enums are reused from the ORM model so the API and the database
can never drift apart.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.model import ModelProvider, ModelType


class ModelOut(BaseModel):
    """Public model configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    provider: ModelProvider
    model_identifier: str
    model_type: ModelType
    is_active: bool
    is_default: bool
    max_tokens: int
    temperature: float
    created_at: datetime
    updated_at: datetime


class ModelCreate(BaseModel):
    """Payload for POST /api/v1/admin/models."""

    name: str = Field(..., min_length=1, max_length=255, examples=["gpt-4o"])
    provider: ModelProvider = ModelProvider.CUSTOM
    model_identifier: str = Field(
        ..., min_length=1, max_length=255, examples=["gpt-4o-2024-08-06"]
    )
    model_type: ModelType = ModelType.CHAT
    is_active: bool = True
    is_default: bool = False
    max_tokens: int = Field(default=128_000, ge=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class ModelUpdate(BaseModel):
    """Payload for PUT /api/v1/admin/models/{model_id}."""

    name: str | None = Field(None, min_length=1, max_length=255)
    provider: ModelProvider | None = None
    model_identifier: str | None = Field(None, min_length=1, max_length=255)
    model_type: ModelType | None = None
    is_default: bool | None = None
    max_tokens: int | None = Field(None, ge=1)
    temperature: float | None = Field(None, ge=0.0, le=2.0)


class ModelStatusUpdate(BaseModel):
    """Payload for PATCH /api/v1/admin/models/{model_id}/status."""

    is_active: bool


class OllamaModelOut(BaseModel):
    """A model installed on the configured Ollama instance."""

    name: str


class OllamaModelsResponse(BaseModel):
    """Response for GET /api/v1/models/ollama."""

    models: list[OllamaModelOut] = Field(default_factory=list)
    default_model: str | None = Field(
        default=None, description="Model selected when a request names none"
    )
