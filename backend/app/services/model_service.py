"""Model configuration service (admin CRUD + public listing).

No LLM is contacted here — this only manages the catalog of models the admin
panel exposes to the frontend.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, not_found
from app.models.model import ModelConfig
from app.schemas.model import ModelCreate, ModelStatusUpdate, ModelUpdate


class ModelService:
    """CRUD over the model catalog."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_models(
        self, offset: int, limit: int, *, active_only: bool = True
    ) -> tuple[list[ModelConfig], int]:
        """One page of models. Regular users only see active ones."""
        stmt = select(ModelConfig)
        count_stmt = select(func.count()).select_from(ModelConfig)
        if active_only:
            stmt = stmt.where(ModelConfig.is_active.is_(True))
            count_stmt = count_stmt.where(ModelConfig.is_active.is_(True))

        total = await self.db.scalar(count_stmt)
        result = await self.db.execute(
            stmt.order_by(ModelConfig.name.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def get_model(self, model_id: UUID) -> ModelConfig:
        """Return a model or raise a 404."""
        return await self._get_or_404(model_id)

    async def create_model(self, data: ModelCreate) -> ModelConfig:
        """Register a new model. Names are unique."""
        await self._assert_name_available(data.name)
        model = ModelConfig(**data.model_dump())
        self.db.add(model)
        await self.db.commit()
        return model

    async def update_model(self, model_id: UUID, data: ModelUpdate) -> ModelConfig:
        """Fully update an existing model."""
        model = await self._get_or_404(model_id)
        payload = data.model_dump(exclude_unset=True)
        if "name" in payload and payload["name"] != model.name:
            await self._assert_name_available(payload["name"])
        for field, value in payload.items():
            setattr(model, field, value)
        await self.db.commit()
        # Reload DB-generated values (e.g. ``updated_at``).
        await self.db.refresh(model)
        return model

    async def set_status(self, model_id: UUID, data: ModelStatusUpdate) -> ModelConfig:
        """Enable or disable a model without touching its other settings."""
        model = await self._get_or_404(model_id)
        model.is_active = data.is_active
        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def delete_model(self, model_id: UUID) -> None:
        """Remove a model from the catalog."""
        model = await self._get_or_404(model_id)
        await self.db.delete(model)
        await self.db.commit()

    async def resolve_default(self) -> str | None:
        """Name of the default active model, if any is configured."""
        result = await self.db.execute(
            select(ModelConfig.name).where(
                ModelConfig.is_active.is_(True), ModelConfig.is_default.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> ModelConfig | None:
        """Return a model by name, or ``None`` when it is not catalogued."""
        result = await self.db.execute(
            select(ModelConfig).where(ModelConfig.name == name)
        )
        return result.scalar_one_or_none()

    async def active_names(self) -> set[str]:
        """Names of every active model — the allow-list for chat requests."""
        result = await self.db.execute(
            select(ModelConfig.name).where(ModelConfig.is_active.is_(True))
        )
        return {name for name in result.scalars().all() if name}

    async def _get_or_404(self, model_id: UUID) -> ModelConfig:
        result = await self.db.execute(
            select(ModelConfig).where(ModelConfig.id == model_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise not_found("Model", model_id)
        return model

    async def _assert_name_available(self, name: str) -> None:
        existing = await self.db.execute(
            select(ModelConfig).where(ModelConfig.name == name)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictException(
                f"A model named {name} already exists.", code="MODEL_NAME_TAKEN"
            )
