"""Prompt management service (admin CRUD + chat lookup).

Follows the ModelService pattern: mutations commit their own transaction and
refresh the row so DB-generated values (``updated_at``) are returned. Chat
only ever reads through :meth:`get_active_default`.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, not_found
from app.models.prompt import PROMPT_STATUS_ACTIVE, Prompt
from app.schemas.prompt import PromptCreate, PromptUpdate


class PromptService:
    """CRUD over the prompt catalog."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_prompts(
        self, offset: int, limit: int, *, active_only: bool = False
    ) -> tuple[list[Prompt], int]:
        """One page of prompts, newest first."""
        stmt = select(Prompt)
        count_stmt = select(func.count()).select_from(Prompt)
        if active_only:
            stmt = stmt.where(Prompt.status == PROMPT_STATUS_ACTIVE)
            count_stmt = count_stmt.where(Prompt.status == PROMPT_STATUS_ACTIVE)

        total = await self.db.scalar(count_stmt)
        result = await self.db.execute(
            stmt.order_by(Prompt.updated_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def get_prompt(self, prompt_id: UUID) -> Prompt:
        """Return a prompt or raise a 404."""
        return await self._get_or_404(prompt_id)

    async def create_prompt(self, data: PromptCreate) -> Prompt:
        """Register a new prompt. Names are unique."""
        await self._assert_name_available(data.name)
        prompt = Prompt(**data.model_dump())
        if prompt.is_default:
            await self._clear_default()
        self.db.add(prompt)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt

    async def update_prompt(self, prompt_id: UUID, data: PromptUpdate) -> Prompt:
        """Partially update a prompt."""
        prompt = await self._get_or_404(prompt_id)
        payload = data.model_dump(exclude_unset=True)
        if "name" in payload and payload["name"] != prompt.name:
            await self._assert_name_available(payload["name"])
        if payload.get("is_default") is True:
            await self._clear_default(exclude_id=prompt.id)
        for field, value in payload.items():
            setattr(prompt, field, value)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt

    async def delete_prompt(self, prompt_id: UUID) -> None:
        """Remove a prompt from the catalog."""
        prompt = await self._get_or_404(prompt_id)
        await self.db.delete(prompt)
        await self.db.commit()

    async def get_active_default(self) -> Prompt | None:
        """The single active default prompt chat uses, if one exists.

        This is the only query the chat path performs against ``prompts``;
        with no rows configured the caller falls back to the built-in
        system-prompt template.
        """
        result = await self.db.execute(
            select(Prompt)
            .where(
                Prompt.is_default.is_(True),
                Prompt.status == PROMPT_STATUS_ACTIVE,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_or_404(self, prompt_id: UUID) -> Prompt:
        result = await self.db.execute(select(Prompt).where(Prompt.id == prompt_id))
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise not_found("Prompt", prompt_id)
        return prompt

    async def _assert_name_available(self, name: str) -> None:
        existing = await self.db.execute(select(Prompt).where(Prompt.name == name))
        if existing.scalar_one_or_none() is not None:
            raise ConflictException(
                f"A prompt named {name} already exists.", code="PROMPT_NAME_TAKEN"
            )

    async def _clear_default(self, exclude_id: UUID | None = None) -> None:
        """Unset every other default so exactly one default exists."""
        stmt = select(Prompt).where(Prompt.is_default.is_(True))
        if exclude_id is not None:
            stmt = stmt.where(Prompt.id != exclude_id)
        result = await self.db.execute(stmt)
        for other in result.scalars().all():
            other.is_default = False
        await self.db.flush()
