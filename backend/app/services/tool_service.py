"""Tool configuration service (admin CRUD + public listing).

Tool *execution* is intentionally out of scope for this phase — this service
only manages the configuration catalog.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, not_found
from app.models.tool import Tool
from app.schemas.tool import ToolCreate, ToolStatusUpdate, ToolUpdate


class ToolService:
    """CRUD over the tool catalog."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_tools(
        self, offset: int, limit: int, *, active_only: bool = True
    ) -> tuple[list[Tool], int]:
        """One page of tools. Regular users only see active ones."""
        stmt = select(Tool)
        count_stmt = select(func.count()).select_from(Tool)
        if active_only:
            stmt = stmt.where(Tool.is_active.is_(True))
            count_stmt = count_stmt.where(Tool.is_active.is_(True))

        total = await self.db.scalar(count_stmt)
        result = await self.db.execute(
            stmt.order_by(Tool.name.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def get_tool(self, tool_id: UUID) -> Tool:
        """Return a tool or raise a 404."""
        return await self._get_or_404(tool_id)

    async def create_tool(self, data: ToolCreate) -> Tool:
        """Register a new tool. Names are unique."""
        await self._assert_name_available(data.name)
        tool = Tool(**data.model_dump())
        self.db.add(tool)
        await self.db.commit()
        return tool

    async def update_tool(self, tool_id: UUID, data: ToolUpdate) -> Tool:
        """Update an existing tool's configuration."""
        tool = await self._get_or_404(tool_id)
        payload = data.model_dump(exclude_unset=True)
        if "name" in payload and payload["name"] != tool.name:
            await self._assert_name_available(payload["name"])
        for field, value in payload.items():
            setattr(tool, field, value)
        await self.db.commit()
        # Reload DB-generated values (e.g. ``updated_at``).
        await self.db.refresh(tool)
        return tool

    async def set_status(self, tool_id: UUID, data: ToolStatusUpdate) -> Tool:
        """Enable or disable a tool."""
        tool = await self._get_or_404(tool_id)
        tool.is_active = data.is_active
        await self.db.commit()
        await self.db.refresh(tool)
        return tool

    async def delete_tool(self, tool_id: UUID) -> None:
        """Remove a tool from the catalog."""
        tool = await self._get_or_404(tool_id)
        await self.db.delete(tool)
        await self.db.commit()

    async def _get_or_404(self, tool_id: UUID) -> Tool:
        result = await self.db.execute(select(Tool).where(Tool.id == tool_id))
        tool = result.scalar_one_or_none()
        if tool is None:
            raise not_found("Tool", tool_id)
        return tool

    async def _assert_name_available(self, name: str) -> None:
        existing = await self.db.execute(select(Tool).where(Tool.name == name))
        if existing.scalar_one_or_none() is not None:
            raise ConflictException(
                f"A tool named {name} already exists.", code="TOOL_NAME_TAKEN"
            )
