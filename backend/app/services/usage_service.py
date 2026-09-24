"""Usage service — allowance enforcement, request recording, analytics.

Single home for every usage concern so route handlers stay thin:

* ``check_allowance``   — reject over-quota requests *before* any LLM work.
* ``record_request``    — persist one :class:`UsageRecord` and bump counters
                          after a request completes (success, failure or
                          cancellation), streamed or not.
* ``get_me``/``summary`` — the authenticated user's own usage view.
* ``admin_*``           — platform analytics aggregated by PostgreSQL.

Counting strategy
-----------------
* **PostgreSQL** is the source of truth: ``usage_records`` (per-request
  history) and ``usage_allowances`` (monthly counters used by the fast
  pre-request check).
* **Redis** holds per-user per-UTC-day counters as an *acceleration* layer
  for the daily limit check. Redis failures are never fatal: reads fall back
  to a PostgreSQL aggregate over ``usage_records`` and write failures are
  logged and skipped.

Usage records are written inside the caller's transaction, so a message and
its usage record commit (or roll back) together.
"""

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UsageLimitExceededException
from app.core.logging import get_logger
from app.models import MessageRole
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.model import ModelConfig
from app.models.usage import (
    REQUEST_STATUS_CANCELLED,
    REQUEST_STATUS_COMPLETED,
    REQUEST_STATUS_FAILED,
    UsageAllowance,
    UsageRecord,
)
from app.models.user import User
from app.schemas.usage import (
    AdminModelUsageRow,
    AdminUsageRow,
    AdminUsageSummary,
    AdminUserUsageRow,
    AllowanceUpdate,
    UsageHistoryItem,
    UsageMeOut,
    UsageSummaryOut,
    UsageTimelinePoint,
)

logger = get_logger(__name__)

# Statuses that consume request quota. A failed provider call (outage, model
# missing, empty response) does not burn the user's request allowance.
BILLABLE_STATUSES = (REQUEST_STATUS_COMPLETED, REQUEST_STATUS_CANCELLED)

# Daily Redis counters live for three days: long enough that today's value is
# always readable, short enough to self-clean.
_DAILY_TTL_SECONDS = 3 * 86400
# Redis is an acceleration layer only — never let it stall a chat request.
_REDIS_TIMEOUT_SECONDS = 2.0


def _next_reset(now: datetime) -> datetime:
    """First moment of the month following ``now`` (UTC)."""
    year, month = now.year, now.month
    if month == 12:
        year, month = year + 1, 1
    else:
        month += 1
    return datetime(year, month, 1, tzinfo=UTC)


def estimate_tokens(text: str) -> int:
    """Best-effort token estimate (~4 characters per token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def resolve_tokens(
    prompt_tokens: int,
    completion_tokens: int,
    *,
    prompt_text: str = "",
    completion_text: str = "",
) -> tuple[int, int, int, bool]:
    """Return ``(prompt, completion, total, is_estimated)``.

    Some Ollama models report no ``prompt_eval_count``/``eval_count``. When a
    count is missing (or zero) it is estimated from the text actually sent or
    received, and ``is_estimated`` becomes ``True`` so estimated usage is
    always distinguishable from provider-reported (actual) usage.
    """
    estimated = False
    if prompt_tokens <= 0 and prompt_text:
        prompt_tokens = estimate_tokens(prompt_text)
        estimated = True
    if completion_tokens <= 0 and completion_text:
        completion_tokens = estimate_tokens(completion_text)
        estimated = True
    prompt_tokens = max(0, prompt_tokens)
    completion_tokens = max(0, completion_tokens)
    return prompt_tokens, completion_tokens, prompt_tokens + completion_tokens, estimated


def resolve_period(
    range_: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> tuple[datetime | None, datetime | None]:
    """Turn API range/date filters into inclusive UTC bounds.

    ``range_`` accepts ``today`` | ``7d`` | ``30d`` | ``all``. An explicit
    ``date_from``/``date_to`` (custom range) always wins over ``range_``.
    """
    if date_from is not None or date_to is not None:
        return (
            _start_of_utc_day(date_from) if date_from else None,
            _end_of_utc_day(date_to) if date_to else None,
        )
    now = datetime.now(UTC)
    if range_ == "today":
        return datetime(now.year, now.month, now.day, tzinfo=UTC), None
    if range_ == "7d":
        return now - timedelta(days=7), None
    if range_ == "30d":
        return now - timedelta(days=30), None
    return None, None  # "all" / unspecified → no time bounds


def _start_of_utc_day(value: datetime) -> datetime:
    value = value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def _end_of_utc_day(value: datetime) -> datetime:
    return _start_of_utc_day(value) + timedelta(days=1) - timedelta(microseconds=1)


class UsageService:
    """Per-user allowances, per-request usage records and usage analytics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Allowance lifecycle -------------------------------------------

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
        """Account for one completed request against the allowance.

        Kept for backwards compatibility; new code should call
        :meth:`record_request`, which also writes the usage record.
        """
        allowance.tokens_used += prompt_tokens + completion_tokens
        allowance.requests_used += 1

    async def get_usage(self, user_id: UUID) -> UsageAllowance:
        """Return (creating if needed) the allowance summary for a user."""
        return await self.get_or_create_allowance(user_id)

    # --- Allowance enforcement -----------------------------------------

    async def check_allowance(self, user_id: UUID) -> UsageAllowance:
        """Raise ``429 USAGE_LIMIT_EXCEEDED`` when the user is over quota.

        Runs *before* any LLM call so an over-quota request never consumes
        model resources. Checks, in order: enabled flag → monthly token /
        request limits → optional daily token / request limits.
        """
        allowance = await self.get_or_create_allowance(user_id)

        if not allowance.is_enabled:
            raise UsageLimitExceededException(
                "Usage allowance is disabled for this account. "
                "Please contact an administrator.",
                code="USAGE_LIMIT_EXCEEDED",
            )

        if (
            allowance.tokens_used >= allowance.monthly_token_limit
            or allowance.requests_used >= allowance.monthly_request_limit
        ):
            raise UsageLimitExceededException(
                "Monthly usage allowance exceeded. Please contact an administrator.",
                code="USAGE_LIMIT_EXCEEDED",
            )

        needs_daily_tokens = allowance.daily_token_limit is not None
        needs_daily_requests = allowance.daily_request_limit is not None
        if needs_daily_tokens or needs_daily_requests:
            tokens_today, requests_today = await self._daily_usage(user_id)
            if needs_daily_tokens and tokens_today >= int(
                allowance.daily_token_limit or 0
            ):
                raise UsageLimitExceededException(
                    "Daily token allowance exceeded. Please try again tomorrow.",
                    code="USAGE_LIMIT_EXCEEDED",
                    details={
                        "limit": allowance.daily_token_limit,
                        "used": tokens_today,
                        "period": "day",
                    },
                )
            if needs_daily_requests and requests_today >= int(
                allowance.daily_request_limit or 0
            ):
                raise UsageLimitExceededException(
                    "Daily request allowance exceeded. Please try again tomorrow.",
                    code="USAGE_LIMIT_EXCEEDED",
                    details={
                        "limit": allowance.daily_request_limit,
                        "used": requests_today,
                        "period": "day",
                    },
                )

        return allowance

    async def remaining_allowance(
        self, user_id: UUID
    ) -> tuple[int, int, int | None, int | None]:
        """``(tokens, requests, tokens_today, requests_today)`` remaining.

        Daily fields are ``None`` when no daily limit is configured.
        """
        allowance = await self.get_or_create_allowance(user_id)
        tokens_today = requests_today = None
        if allowance.daily_token_limit is not None or (
            allowance.daily_request_limit is not None
        ):
            used_tokens, used_requests = await self._daily_usage(user_id)
            tokens_today = (
                None
                if allowance.daily_token_limit is None
                else max(0, allowance.daily_token_limit - used_tokens)
            )
            requests_today = (
                None
                if allowance.daily_request_limit is None
                else max(0, allowance.daily_request_limit - used_requests)
            )
        return (
            allowance.tokens_remaining,
            allowance.requests_remaining,
            tokens_today,
            requests_today,
        )

    # --- Request recording ---------------------------------------------

    async def record_request(
        self,
        *,
        user_id: UUID,
        model: str,
        provider: str,
        conversation_id: UUID | None = None,
        message_id: UUID | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        duration_ms: float | None = None,
        status: str = REQUEST_STATUS_COMPLETED,
        error: dict[str, Any] | None = None,
        prompt_text: str = "",
        completion_text: str = "",
    ) -> UsageRecord:
        """Record one completed (or failed/cancelled) LLM request.

        Writes the :class:`UsageRecord` into the caller's session — committed
        together with the chat message so both stay consistent — then bumps
        the monthly allowance counters and the Redis daily counters. Counter
        and Redis failures are logged but never raised: usage bookkeeping must
        not destroy an otherwise successful chat response.
        """
        p_tokens, c_tokens, total, estimated = resolve_tokens(
            prompt_tokens,
            completion_tokens,
            prompt_text=prompt_text,
            completion_text=completion_text,
        )

        record = UsageRecord(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            model=model,
            provider=provider,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=total,
            is_estimated=estimated,
            request_timestamp=datetime.now(UTC),
            response_duration_ms=(
                None if duration_ms is None else max(0, round(duration_ms))
            ),
            request_status=status,
            error_info=error,
        )
        self.db.add(record)

        billable = status in BILLABLE_STATUSES
        try:
            allowance = await self.get_or_create_allowance(user_id)
            allowance.tokens_used += total
            if billable:
                allowance.requests_used += 1
        except Exception:
            logger.exception(
                "Failed to update allowance counters user=%s status=%s",
                user_id,
                status,
            )

        await self._bump_daily(
            user_id, tokens=total, requests=1 if billable else 0
        )
        return record

    # --- Personal views -------------------------------------------------

    async def get_me(self, user_id: UUID) -> UsageMeOut:
        """Full personal usage view (own data only)."""
        allowance = await self.get_or_create_allowance(user_id)
        tokens_today, requests_today = await self._daily_usage(user_id)

        return UsageMeOut(
            tokens_today=tokens_today,
            requests_today=requests_today,
            tokens_remaining_today=(
                None
                if allowance.daily_token_limit is None
                else max(0, allowance.daily_token_limit - tokens_today)
            ),
            requests_remaining_today=(
                None
                if allowance.daily_request_limit is None
                else max(0, allowance.daily_request_limit - requests_today)
            ),
            tokens_this_month=allowance.tokens_used,
            requests_this_month=allowance.requests_used,
            tokens_remaining=allowance.tokens_remaining,
            requests_remaining=allowance.requests_remaining,
            monthly_token_limit=allowance.monthly_token_limit,
            monthly_request_limit=allowance.monthly_request_limit,
            daily_token_limit=allowance.daily_token_limit,
            daily_request_limit=allowance.daily_request_limit,
            is_enabled=allowance.is_enabled,
            is_allowed=allowance.is_allowed,
            reset_at=allowance.reset_at,
            current_model=await self._current_model(),
        )

    async def get_summary(self, user_id: UUID) -> UsageSummaryOut:
        """Compact personal usage summary (own data only)."""
        me = await self.get_me(user_id)
        return UsageSummaryOut(
            tokens_today=me.tokens_today,
            requests_today=me.requests_today,
            tokens_this_month=me.tokens_this_month,
            requests_this_month=me.requests_this_month,
            tokens_remaining=me.tokens_remaining,
            requests_remaining=me.requests_remaining,
            current_model=me.current_model,
        )

    async def _current_model(self) -> str | None:
        """Model the chat UI resolves to when the request names none."""
        result = await self.db.execute(
            select(ModelConfig.name).where(
                ModelConfig.is_active.is_(True),
                ModelConfig.is_default.is_(True),
            )
        )
        name = result.scalar_one_or_none()
        return name or settings.ollama_default_model or None

    # --- Redis daily counters (with PostgreSQL fallback) ----------------

    @staticmethod
    def _daily_keys(user_id: UUID, day: date) -> tuple[str, str]:
        prefix = f"usage:{user_id}:{day.isoformat()}"
        return f"{prefix}:tokens", f"{prefix}:requests"

    async def _bump_daily(self, user_id: UUID, *, tokens: int, requests: int) -> None:
        """Best-effort increment of today's Redis counters."""
        from app.core.redis import redis_client

        tokens_key, requests_key = self._daily_keys(user_id, datetime.now(UTC).date())
        try:
            pipe = redis_client.pipeline()
            pipe.incrby(tokens_key, max(0, tokens))
            pipe.incrby(requests_key, max(0, requests))
            pipe.expire(tokens_key, _DAILY_TTL_SECONDS)
            pipe.expire(requests_key, _DAILY_TTL_SECONDS)
            await asyncio.wait_for(pipe.execute(), timeout=_REDIS_TIMEOUT_SECONDS)
        except Exception as exc:  # noqa: BLE001 — Redis is never fatal
            logger.warning(
                "Failed to increment Redis usage counters user=%s: %s",
                user_id,
                exc,
            )

    async def _daily_usage(self, user_id: UUID) -> tuple[int, int]:
        """``(tokens, requests)`` used by the user during the current UTC day."""
        day = datetime.now(UTC).date()
        cached = await self._read_daily_from_redis(user_id, day)
        if cached is not None:
            return cached
        return await self._daily_usage_from_db(user_id, day)

    async def _read_daily_from_redis(
        self, user_id: UUID, day: date
    ) -> tuple[int, int] | None:
        """Read today's counters; ``None`` when Redis cannot be trusted."""
        from app.core.redis import redis_client

        tokens_key, requests_key = self._daily_keys(user_id, day)
        try:
            values = await asyncio.wait_for(
                redis_client.mget(tokens_key, requests_key),
                timeout=_REDIS_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001 — fall back to PostgreSQL
            logger.warning(
                "Failed to read Redis usage counters user=%s (falling back "
                "to PostgreSQL): %s",
                user_id,
                exc,
            )
            return None
        # A missing key means the counters were never written (e.g. Redis was
        # restarted mid-day) — PostgreSQL remains the source of truth.
        if not values or values[0] is None or values[1] is None:
            return None
        try:
            return int(values[0]), int(values[1])
        except (TypeError, ValueError):
            return None

    async def _daily_usage_from_db(self, user_id: UUID, day: date) -> tuple[int, int]:
        """Aggregate today's usage straight from ``usage_records``."""
        start = datetime(day.year, day.month, day.day, tzinfo=UTC)
        row = (
            await self.db.execute(
                select(
                    func.coalesce(func.sum(UsageRecord.total_tokens), 0),
                    func.count(UsageRecord.id).filter(
                        UsageRecord.request_status.in_(BILLABLE_STATUSES)
                    ),
                ).where(
                    UsageRecord.user_id == user_id,
                    UsageRecord.request_timestamp >= start,
                )
            )
        ).one()
        return int(row[0] or 0), int(row[1] or 0)

    # --- Admin configuration -------------------------------------------

    async def admin_update_allowance(
        self, user_id: UUID, data: AllowanceUpdate
    ) -> UsageAllowance:
        """Update a user's configurable limits.

        Fields present in the payload are applied even when ``None`` so an
        admin can clear a daily limit (set it back to unlimited).
        """
        allowance = await self.get_or_create_allowance(user_id)
        if data.monthly_token_limit is not None:
            allowance.monthly_token_limit = data.monthly_token_limit
        if data.monthly_request_limit is not None:
            allowance.monthly_request_limit = data.monthly_request_limit
        if "daily_token_limit" in data.model_fields_set:
            allowance.daily_token_limit = data.daily_token_limit
        if "daily_request_limit" in data.model_fields_set:
            allowance.daily_request_limit = data.daily_request_limit
        if data.is_enabled is not None:
            allowance.is_enabled = data.is_enabled
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

    # --- Personal history ----------------------------------------------

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

    # --- Admin analytics (over usage_records) ---------------------------

    @staticmethod
    def _record_filters(
        *,
        date_from: datetime | None,
        date_to: datetime | None,
        model: str | None = None,
        user_id: UUID | None = None,
    ) -> list[Any]:
        conditions: list[Any] = []
        if date_from is not None:
            conditions.append(UsageRecord.request_timestamp >= date_from)
        if date_to is not None:
            conditions.append(UsageRecord.request_timestamp <= date_to)
        if model:
            conditions.append(UsageRecord.model == model)
        if user_id is not None:
            conditions.append(UsageRecord.user_id == user_id)
        return conditions

    @staticmethod
    def _avg_ms(value: Any) -> float | None:
        return None if value is None else round(float(value), 1)

    async def admin_summary(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        model: str | None = None,
        user_id: UUID | None = None,
    ) -> AdminUsageSummary:
        """Platform-wide request/token totals for the filtered period."""
        stmt = select(
            func.count(UsageRecord.id),
            func.count(UsageRecord.id).filter(
                UsageRecord.request_status == REQUEST_STATUS_COMPLETED
            ),
            func.count(UsageRecord.id).filter(
                UsageRecord.request_status == REQUEST_STATUS_FAILED
            ),
            func.count(UsageRecord.id).filter(
                UsageRecord.request_status == REQUEST_STATUS_CANCELLED
            ),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0),
            func.coalesce(func.sum(UsageRecord.prompt_tokens), 0),
            func.coalesce(func.sum(UsageRecord.completion_tokens), 0),
            func.count(func.distinct(UsageRecord.user_id)),
            func.avg(UsageRecord.response_duration_ms),
        )
        conditions = self._record_filters(
            date_from=date_from, date_to=date_to, model=model, user_id=user_id
        )
        if conditions:
            stmt = stmt.where(*conditions)
        row = (await self.db.execute(stmt)).one()
        return AdminUsageSummary(
            total_requests=int(row[0] or 0),
            successful_requests=int(row[1] or 0),
            failed_requests=int(row[2] or 0),
            cancelled_requests=int(row[3] or 0),
            total_tokens=int(row[4] or 0),
            prompt_tokens=int(row[5] or 0),
            completion_tokens=int(row[6] or 0),
            active_users=int(row[7] or 0),
            average_response_time_ms=self._avg_ms(row[8]),
        )

    async def admin_by_model(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        model: str | None = None,
        user_id: UUID | None = None,
    ) -> list[AdminModelUsageRow]:
        """Usage aggregated per model, biggest token consumers first."""
        stmt = select(
            UsageRecord.model,
            func.max(UsageRecord.provider),
            func.count(UsageRecord.id),
            func.count(UsageRecord.id).filter(
                UsageRecord.request_status == REQUEST_STATUS_COMPLETED
            ),
            func.count(UsageRecord.id).filter(
                UsageRecord.request_status == REQUEST_STATUS_FAILED
            ),
            func.coalesce(func.sum(UsageRecord.prompt_tokens), 0),
            func.coalesce(func.sum(UsageRecord.completion_tokens), 0),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0),
            func.avg(UsageRecord.response_duration_ms),
        )
        conditions = self._record_filters(
            date_from=date_from, date_to=date_to, model=model, user_id=user_id
        )
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.group_by(UsageRecord.model).order_by(
            func.sum(UsageRecord.total_tokens).desc()
        )
        result = await self.db.execute(stmt)
        return [
            AdminModelUsageRow(
                model=row[0],
                provider=row[1],
                requests=int(row[2] or 0),
                successful_requests=int(row[3] or 0),
                failed_requests=int(row[4] or 0),
                prompt_tokens=int(row[5] or 0),
                completion_tokens=int(row[6] or 0),
                total_tokens=int(row[7] or 0),
                average_response_time_ms=self._avg_ms(row[8]),
            )
            for row in result
        ]

    async def admin_by_user(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        model: str | None = None,
        user_id: UUID | None = None,
    ) -> list[AdminUserUsageRow]:
        """Usage aggregated per user, biggest token consumers first."""
        stmt = (
            select(
                UsageRecord.user_id,
                User.email,
                User.name,
                func.count(UsageRecord.id),
                func.count(UsageRecord.id).filter(
                    UsageRecord.request_status == REQUEST_STATUS_COMPLETED
                ),
                func.count(UsageRecord.id).filter(
                    UsageRecord.request_status == REQUEST_STATUS_FAILED
                ),
                func.coalesce(func.sum(UsageRecord.prompt_tokens), 0),
                func.coalesce(func.sum(UsageRecord.completion_tokens), 0),
                func.coalesce(func.sum(UsageRecord.total_tokens), 0),
                func.avg(UsageRecord.response_duration_ms),
            )
            .join(User, User.id == UsageRecord.user_id)
        )
        conditions = self._record_filters(
            date_from=date_from, date_to=date_to, model=model, user_id=user_id
        )
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.group_by(
            UsageRecord.user_id, User.email, User.name
        ).order_by(func.sum(UsageRecord.total_tokens).desc())
        result = await self.db.execute(stmt)
        return [
            AdminUserUsageRow(
                user_id=row[0],
                email=row[1],
                name=row[2],
                requests=int(row[3] or 0),
                successful_requests=int(row[4] or 0),
                failed_requests=int(row[5] or 0),
                prompt_tokens=int(row[6] or 0),
                completion_tokens=int(row[7] or 0),
                total_tokens=int(row[8] or 0),
                average_response_time_ms=self._avg_ms(row[9]),
            )
            for row in result
        ]

    async def admin_timeline(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        model: str | None = None,
        user_id: UUID | None = None,
    ) -> list[UsageTimelinePoint]:
        """Daily usage over time (newest day first)."""
        period = func.date_trunc("day", UsageRecord.request_timestamp)
        stmt = select(
            period,
            func.count(UsageRecord.id),
            func.count(UsageRecord.id).filter(
                UsageRecord.request_status == REQUEST_STATUS_FAILED
            ),
            func.coalesce(func.sum(UsageRecord.prompt_tokens), 0),
            func.coalesce(func.sum(UsageRecord.completion_tokens), 0),
            func.coalesce(func.sum(UsageRecord.total_tokens), 0),
            func.avg(UsageRecord.response_duration_ms),
        )
        conditions = self._record_filters(
            date_from=date_from, date_to=date_to, model=model, user_id=user_id
        )
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.group_by(period).order_by(period.desc())
        result = await self.db.execute(stmt)
        return [
            UsageTimelinePoint(
                period=row[0].date(),
                requests=int(row[1] or 0),
                failed_requests=int(row[2] or 0),
                prompt_tokens=int(row[3] or 0),
                completion_tokens=int(row[4] or 0),
                total_tokens=int(row[5] or 0),
                average_response_time_ms=self._avg_ms(row[6]),
            )
            for row in result
        ]
