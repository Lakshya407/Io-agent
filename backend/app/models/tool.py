"""Tool configuration model. Execution is out of scope for this phase."""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import Enum, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models import TimestampMixin


class ToolType(StrEnum):
    """Coarse tool categories (mirrors the frontend categories)."""

    SEARCH = "search"
    KNOWLEDGE = "knowledge"
    UTILITY = "utility"
    DEVELOPMENT = "development"
    ANALYTICS = "analytics"
    MEDIA = "media"


class Tool(Base, TimestampMixin):
    """An agent tool configuration. Stored as configuration only — not run."""

    __tablename__ = "tools"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[ToolType] = mapped_column(
        Enum(ToolType, native_enum=False, length=20),
        nullable=False,
        default=ToolType.UTILITY,
        server_default=ToolType.UTILITY.value,
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'")
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default=text("true")
    )

    def __repr__(self) -> str:
        return f"<Tool {self.name!r} active={self.is_active}>"
