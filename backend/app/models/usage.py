"""Usage models — per-user allowances and per-request usage records.

Two complementary tables:

* :class:`UsageAllowance` — the *quota*: monthly counters plus configurable
  monthly/daily limits. It is small, one row per user, and is the fast
  "is this user allowed to send another request?" check.
* :class:`UsageRecord` — the *history*: exactly one row per LLM request
  (completed, failed or cancelled) with token accounting, latency and error
  details. Analytics (admin dashboard, usage over time, per-model/per-user
  breakdowns) read from this table; it intentionally survives conversation
  deletion (``SET NULL``) so usage history is independent of chat history.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

# Sensible defaults; admins can change these per user via the admin API.
DEFAULT_MONTHLY_TOKEN_LIMIT = 10_000_000
DEFAULT_MONTHLY_REQUEST_LIMIT = 1_000
# Daily limits default to NULL (= no daily cap) so upgrading never
# unexpectedly blocks existing users; admins opt in per user.
DEFAULT_DAILY_TOKEN_LIMIT = None
DEFAULT_DAILY_REQUEST_LIMIT = None

# Request lifecycle recorded on every usage record.
REQUEST_STATUS_COMPLETED = "completed"
REQUEST_STATUS_FAILED = "failed"
REQUEST_STATUS_CANCELLED = "cancelled"
REQUEST_STATUSES = (
    REQUEST_STATUS_COMPLETED,
    REQUEST_STATUS_FAILED,
    REQUEST_STATUS_CANCELLED,
)


class UsageAllowance(Base, TimestampMixin):
    """Monthly (and optionally daily) token/request allowance for one user."""

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
    # Optional daily caps (NULL = unlimited).
    daily_token_limit: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=DEFAULT_DAILY_TOKEN_LIMIT
    )
    daily_request_limit: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=DEFAULT_DAILY_REQUEST_LIMIT
    )
    # Admin kill-switch: when disabled the user cannot send LLM requests.
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
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
        if not self.is_enabled:
            return False
        return (
            self.tokens_used < self.monthly_token_limit
            and self.requests_used < self.monthly_request_limit
        )

    def __repr__(self) -> str:
        return (
            f"<UsageAllowance user={self.user_id} "
            f"tokens={self.tokens_used}/{self.monthly_token_limit}>"
        )


class UsageRecord(Base):
    """One LLM request: token accounting, latency, status and error info."""

    __tablename__ = "usage_records"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # SET NULL on delete: usage history outlives the conversation/message.
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    model: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    # True when the provider reported no counts (some Ollama models do not)
    # and the token numbers were derived from text length instead.
    is_estimated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    request_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        server_default=text("now()"),
        nullable=False,
    )
    response_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # completed | failed | cancelled (see REQUEST_STATUSES).
    request_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=REQUEST_STATUS_COMPLETED,
        server_default=text("'completed'"),
    )
    # {"code": ..., "message": ...} for failed requests; NULL otherwise.
    error_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<UsageRecord model={self.model} status={self.request_status} "
            f"tokens={self.total_tokens}>"
        )
