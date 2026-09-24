"""Prompt management model — admin-editable system prompts.

Exactly one prompt may have ``is_default`` (enforced by a partial unique
index). Chat uses the active default prompt's content as the system
instruction and falls back to the built-in template when none exists, so an
empty table keeps historical behaviour.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models import TimestampMixin

# Lifecycle shown in the admin console (StatusBadge colours match these).
PROMPT_STATUS_ACTIVE = "active"
PROMPT_STATUS_DRAFT = "draft"
PROMPT_STATUS_INACTIVE = "inactive"
PROMPT_STATUSES = (
    PROMPT_STATUS_ACTIVE,
    PROMPT_STATUS_DRAFT,
    PROMPT_STATUS_INACTIVE,
)


class Prompt(Base, TimestampMixin):
    """One named system prompt with versioning metadata."""

    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    purpose: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", server_default=text("''")
    )
    # Optional target model (informational — prompts are not model-bound).
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PROMPT_STATUS_DRAFT,
        server_default=text("'draft'"),
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # The single default prompt chat actually uses (partial unique index).
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    def __repr__(self) -> str:
        return f"<Prompt {self.name} v{self.version} {self.status}>"
