"""Usage allowance model — enforces per-user monthly token/request limits."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

# Sensible defaults; admins can change these per user via the admin API.
DEFAULT_MONTHLY_TOKEN_LIMIT = 10_000_000
DEFAULT_MONTHLY_REQUEST_LIMIT = 1_000


class UsageAllowance(Base, TimestampMixin):
    """Monthly token/request allowance for a single user."""

    __tablename__ = "usage_allowances"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    monthly_token_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=DEFAULT_MONTHLY_TOKEN_LIMIT,
        server_default=str(DEFAULT_MONTHLY_TOKEN_LIMIT),
    )
    monthly_request_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=DEFAULT_MONTHLY_REQUEST_LIMIT,
        server_default=str(DEFAULT_MONTHLY_REQUEST_LIMIT),
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    requests_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="usage_allowance")

    @property
    def tokens_remaining(self) -> int:
        """Remaining tokens for the current period (never negative)."""
        return max(0, self.monthly_token_limit - self.tokens_used)

    @property
    def requests_remaining(self) -> int:
        """Remaining requests for the current period (never negative)."""
        return max(0, self.monthly_request_limit - self.requests_used)

    @property
    def is_allowed(self) -> bool:
        """Whether the user is still within both token and request limits."""
        return (
            self.tokens_used < self.monthly_token_limit
            and self.requests_used < self.monthly_request_limit
        )

    def __repr__(self) -> str:
        return (
            f"<UsageAllowance user={self.user_id} "
            f"tokens={self.tokens_used}/{self.monthly_token_limit}>"
        )
