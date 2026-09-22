"""Usage allowance service.

Implements the three things the platform needs to know about a user's quota
(``allowed?``, ``remaining tokens?``, ``remaining requests?``) plus the
aggregated history views used by the admin panel.

All counting is done by PostgreSQL; usage rows are never loaded into Python.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import not_found
from app.models import MessageRole
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.model import ModelConfig
from app.models.usage import UsageAllowance
from app.models.user import User
from app.schemas.usage import AdminUsageRow, AllowanceUpdate, UsageHistoryItem


def _next_reset(now: datetime) -> datetime:
    """First moment of the month following ``now`` (UTC)."""
    year, month = now.year, now.month
    if month == 12:
        year, month = year + 1, 1
    else:
        month += 1
    return datetime(year, month, 1, tzinfo=UTC)


class UsageService:
    """Per-user monthly token/request allowances."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_for_user(self, user_id: UUID) -> UsageAllowance:
        """Provision a default allowance for a brand-new user."""
        allowance = UsageAllowance(
            user_id=user_id, reset_at=_next_reset(datetime.now(UTC))
        )
        self.db.add(allowance)
        await self.db.flush()
        return allowance

    async def get_or_create_allowance(self, user_id: UUID) -> UsageAllowance:
        """Return the user's allowance, auto-resetting when the month rolls over."""
        result = await self.db.execute(
            select(UsageAllowance).where(UsageAllowance.user_id == user_id)
        )
        allowance = result.scalar_one_or_none()

        if allowance is None:
            return await self.create_for_user(user_id)

        await self._maybe_reset(allowance)
        return allowance

    async def _maybe_reset(self, allowance: UsageAllowance) -> None:
        """Zero the counters once the current period has ended."""
        now = datetime.now(UTC)
        if now >= allowance.reset_at:
            allowance.tokens_used = 0
            allowance.requests_used = 0
            allowance.reset_at = _next_reset(now)

    async def record_usage(
        self, allowance: UsageAllowance, prompt_tokens: int, completion_tokens: int
    ) -> None:
        """Account for one completed request against the allowance."""
        allowance.tokens_used += prompt_tokens + completion_tokens
        allowance.requests_used += 1

    async def get_usage(self, user_id: UUID) -> UsageAllowance:
        """Return (creating if needed) the allowance summary for a user."""
        return await self.get_or_create_allowance(user_id)

    async def admin_update_allowance(
        self, user_id: UUID, data: AllowanceUpdate
    ) -> UsageAllowance:
        """Update a user's configurable limits."""
        allowance = await self.get_or_create_allowance(user_id)
        if data.monthly_token_limit is not None:
            allowance.monthly_token_limit = data.monthly_token_limit
        if data.monthly_request_limit is not None:
            allowance.monthly_request_limit = data.monthly_request_limit
        if data.reset_at is not None:
            allowance.reset_at = data.reset_at
        await self.db.commit()
        return allowance

    async def admin_list_usage(
        self, offset: int, limit: int
    ) -> tuple[list[AdminUsageRow], int]:
        """One page of every user's allowance joined with their identity.

        Projection is done in SQL; only the page of rows is transferred.
        """
        total = await self.db.scalar(
            select(func.count()).select_from(UsageAllowance)
        )

        stmt = (
            select(
                UsageAllowance.user_id.label("user_id"),
                User.email.label("email"),
                User.name.label("name"),
                User.role.label("role"),
                UsageAllowance.monthly_token_limit.label("monthly_token_limit"),
                UsageAllowance.monthly_request_limit.label("monthly_request_limit"),
                UsageAllowance.tokens_used.label("tokens_used"),
                UsageAllowance.requests_used.label("requests_used"),
                UsageAllowance.reset_at.label("reset_at"),
            )
            .join(User, User.id == UsageAllowance.user_id)
            .order_by(UsageAllowance.tokens_used.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)

        rows: list[AdminUsageRow] = []
        for row in result:
            used_tokens = int(row.tokens_used)
            limit_tokens = int(row.monthly_token_limit)
            used_requests = int(row.requests_used)
            limit_requests = int(row.monthly_request_limit)
            rows.append(
                AdminUsageRow(
                    user_id=row.user_id,
                    email=row.email,
                    name=row.name,
                    role=row.role.value if row.role else "user",
                    monthly_token_limit=limit_tokens,
                    monthly_request_limit=limit_requests,
                    tokens_used=used_tokens,
                    requests_used=used_requests,
                    tokens_remaining=max(0, limit_tokens - used_tokens),
                    requests_remaining=max(0, limit_requests - used_requests),
                    reset_at=row.reset_at,
                )
            )
        return rows, int(total or 0)

    async def history(
        self,
        user_id: UUID,
        offset: int,
        limit: int,
        *,
        model: str | None = None,
        provider: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[UsageHistoryItem], int]:
        """Aggregated daily usage for a user, filterable by date/model/provider.

        Grouping and summing happen in PostgreSQL. Each chat round is counted
        once, keyed on the assistant completion (which carries the model and
        token accounting).
        """
        period = func.date_trunc("day", Message.created_at).label("period")

        base = (
            select(
                period,
                # One request per assistant completion (never per stored row).
                func.count()
                .filter(Message.role == MessageRole.ASSISTANT)
                .label("requests"),
                func.coalesce(func.sum(Message.total_tokens), 0).label("tokens"),
            )
            .join(Conversation, Conversation.id == Message.conversation_id)
            .outerjoin(ModelConfig, ModelConfig.name == Message.model)
            .where(Conversation.user_id == user_id)
        )
        if model is not None:
            base = base.where(Message.model == model)
        if provider is not None:
            base = base.where(ModelConfig.provider == provider)
        if date_from is not None:
            base = base.where(Message.created_at >= date_from)
        if date_to is not None:
            base = base.where(Message.created_at <= date_to)

        aggregated = base.group_by(period).order_by(period.desc())

        total = await self.db.scalar(
            select(func.count()).select_from(aggregated.subquery())
        )

        page = await self.db.execute(aggregated.offset(offset).limit(limit))

        items = [
            UsageHistoryItem(
                period=row.period.date(),
                requests=int(row.requests),
                tokens=int(row.tokens),
            )
            for row in page
        ]
        return items, int(total or 0)
