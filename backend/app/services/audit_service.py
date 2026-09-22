"""Reusable audit logging service.

Every privileged or security-relevant action is recorded as an immutable
:class:`~app.models.audit_log.AuditLog` row. Failures here must never break
the calling request, so callers wrap invocations in ``try/except``.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit_log import AuditAction, AuditLog

logger = get_logger(__name__)


class AuditService:
    """Writes audit events to the database session."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        *,
        action: AuditAction,
        resource_type: str,
        user_id: UUID | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        """Persist a single audit event and flush it to the session.

        Returns the created row, or ``None`` when the write failed (the error
        is logged instead of propagated).
        """
        try:
            entry = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_=metadata or {},
            )
            self.db.add(entry)
            await self.db.flush()
            return entry
        except Exception:
            # Auditing is best-effort; it must never take down a request.
            logger.exception("Failed to write audit log for %s", action)
            return None
