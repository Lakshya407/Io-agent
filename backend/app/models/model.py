"""Model configuration — the models the Admin Panel makes available."""

import uuid
from enum import StrEnum

from sqlalchemy import Enum, Float, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models import TimestampMixin


class ModelProvider(StrEnum):
    """Supported (future) LLM providers. Not integrated yet."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class ModelType(StrEnum):
    """Broad category of what a model is used for."""

    CHAT = "chat"
    CODE = "code"
    EMBEDDING = "embedding"


class ModelConfig(Base, TimestampMixin):
    """A configurable LLM the platform can route requests to."""

    __tablename__ = "models"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    provider: Mapped[ModelProvider] = mapped_column(
        Enum(ModelProvider, native_enum=False, length=20),
        nullable=False,
        default=ModelProvider.CUSTOM,
        server_default=ModelProvider.CUSTOM.value,
    )
    model_identifier: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    model_type: Mapped[ModelType] = mapped_column(
        Enum(ModelType, native_enum=False, length=20),
        nullable=False,
        default=ModelType.CHAT,
        server_default=ModelType.CHAT.value,
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default=text("true")
    )
    is_default: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=text("false")
    )
    max_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=128_000, server_default=text("128000")
    )
    temperature: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.7, server_default=text("0.7")
    )

    def __repr__(self) -> str:
        return f"<ModelConfig {self.name!r} provider={self.provider}>"
