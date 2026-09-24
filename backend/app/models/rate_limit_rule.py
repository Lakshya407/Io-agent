"""Rate limit rules — DB-configurable limits for the Redis rate limiter.

An empty table means "fall back to the built-in ``RATE_LIMIT_PER_*``
settings", so a fresh install behaves exactly as before. Rules created
through the admin console become the source of truth; the effective set is
cached briefly in Redis (see ``app.services.rate_limit_service``).

Scopes:
* ``all``  — applies to every request
* ``user`` — applies to authenticated requests only
* ``ip``   — applies to unauthenticated (IP-identified) requests only
"""

import uuid

from sqlalchemy import Boolean, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models import TimestampMixin

SCOPE_ALL = "all"
SCOPE_USER = "user"
SCOPE_IP = "ip"
SCOPES = (SCOPE_ALL, SCOPE_USER, SCOPE_IP)

# Only "block" (429) is enforced today; the column exists so additional
# actions can be introduced without a schema change.
ACTION_BLOCK = "block"


class RateLimitRule(Base, TimestampMixin):
    """One limit: ``limit`` requests per ``window_seconds`` for a scope."""

    __tablename__ = "rate_limit_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    scope: Mapped[str] = mapped_column(
        String(50), nullable=False, default=SCOPE_ALL, server_default=text("'all'")
    )
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ACTION_BLOCK, server_default=text("'block'")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true"),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<RateLimitRule {self.scope} {self.limit}/{self.window_seconds}s>"
