"""Admin dashboard service.

Every statistic is computed by a SQL aggregate so the dashboard never loads
individual rows into Python.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model import ModelConfig
from app.models.tool import Tool
from app.models.usage import UsageAllowance
from app.models.user import User
from app.schemas.admin import DashboardStats


async def get_dashboard_stats(db: AsyncSession) -> DashboardStats:
    """Aggregate platform-wide statistics in a handful of cheap queries."""
    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    active_users = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.is_active.is_(True))
    ) or 0
    total_requests = await db.scalar(
        select(func.coalesce(func.sum(UsageAllowance.requests_used), 0))
    ) or 0
    total_tokens = await db.scalar(
        select(func.coalesce(func.sum(UsageAllowance.tokens_used), 0))
    ) or 0
    active_models = await db.scalar(
        select(func.count())
        .select_from(ModelConfig)
        .where(ModelConfig.is_active.is_(True))
    ) or 0
    active_tools = await db.scalar(
        select(func.count())
        .select_from(Tool)
        .where(Tool.is_active.is_(True))
    ) or 0

    return DashboardStats(
        total_users=int(total_users),
        active_users=int(active_users),
        total_requests=int(total_requests),
        total_tokens=int(total_tokens),
        active_models=int(active_models),
        active_tools=int(active_tools),
    )
