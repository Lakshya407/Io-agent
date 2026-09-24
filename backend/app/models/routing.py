"""Model routing rules — request type → primary/fallback model.

Applied by ChatService when a request names no explicit model: the first
active rule matching the request's ``request_type`` (priority order) whose
model is still in the active catalog wins; otherwise default resolution runs.
"""

import uuid

from sqlalchemy import Boolean, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models import TimestampMixin


class RoutingRule(Base, TimestampMixin):
    """One priority-ordered routing rule."""

    __tablename__ = "routing_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    request_type: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    primary_model: Mapped[str] = mapped_column(String(255), nullable=False)
    fallback_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    def __repr__(self) -> str:
        return f"<RoutingRule {self.request_type} -> {self.primary_model}>"
