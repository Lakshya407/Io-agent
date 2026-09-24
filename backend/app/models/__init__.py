"""SQLAlchemy models package.

Importing this package registers every model with the declarative metadata
(Alembic relies on this when generating migrations).
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class TimestampMixin:
    """Mixin adding ``created_at`` / ``updated_at`` columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserRole(StrEnum):
    """User roles used for authorization."""

    ADMIN = "admin"
    USER = "user"


class MessageRole(StrEnum):
    """Roles a chat message can have."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# Import all models so their tables are registered on Base.metadata.
from app.models import (  # noqa: E402,F401  (order matters for relationships)
    api_key,
    audit_log,
    conversation,
    message,
    model,
    prompt,
    rate_limit_rule,
    routing,
    tool,
    usage,
    user,
)

__all__ = ["Base", "TimestampMixin", "UserRole", "MessageRole"]
