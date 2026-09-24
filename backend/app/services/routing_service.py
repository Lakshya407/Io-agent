"""Model routing service (admin CRUD + chat-time resolution).

Resolution rules — the first *active* rule whose ``request_type`` matches,
in priority order:

1. ``primary_model`` when it is still allowed to run (active catalog entry,
   the configured default, or the built-in fallback),
2. otherwise ``fallback_model`` under the same check,
3. otherwise the next matching rule; finally ``None`` → default resolution.

This keeps routing inside the existing model allow-list: a rule can never
make chat run a model the catalog has disabled.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, ValidationException, not_found
from app.models.model import ModelConfig
from app.models.routing import RoutingRule
from app.schemas.routing import RoutingRuleCreate, RoutingRuleUpdate

# Built-in model names chat_service accepts even without a catalog entry.
_BUILT_IN_MODELS = {"mock"}


class RoutingService:
    """CRUD over routing rules + request-time model resolution."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_rules(self) -> list[RoutingRule]:
        """Every rule, highest priority first."""
        result = await self.db.execute(
            select(RoutingRule).order_by(RoutingRule.priority.asc())
        )
        return list(result.scalars().all())

    async def create_rule(self, data: RoutingRuleCreate) -> RoutingRule:
        """Add a rule at the lowest priority (appended to the end)."""
        await self._assert_request_type_available(data.request_type)
        await self._assert_model_exists(data.primary_model, required=True)
        if data.fallback_model:
            await self._assert_model_exists(data.fallback_model, required=False)

        highest = await self.db.scalar(
            select(func.max(RoutingRule.priority))
        ) or 0
        rule = RoutingRule(**data.model_dump(), priority=highest + 1)
        self.db.add(rule)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def update_rule(
        self, rule_id: UUID, data: RoutingRuleUpdate
    ) -> RoutingRule:
        """Partially update a rule (models are re-validated when changed)."""
        rule = await self._get_or_404(rule_id)
        payload = data.model_dump(exclude_unset=True)

        if "request_type" in payload and payload["request_type"] != rule.request_type:
            await self._assert_request_type_available(payload["request_type"])
        if "primary_model" in payload:
            await self._assert_model_exists(payload["primary_model"], required=True)
        if "fallback_model" in payload and payload["fallback_model"]:
            await self._assert_model_exists(payload["fallback_model"], required=False)
        # ``None`` fallback means "no fallback" — only reject an empty string.
        if payload.get("fallback_model") == "":
            payload["fallback_model"] = None

        for field, value in payload.items():
            setattr(rule, field, value)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def delete_rule(self, rule_id: UUID) -> None:
        """Remove a rule and renumber the remainder."""
        rule = await self._get_or_404(rule_id)
        await self.db.delete(rule)
        await self.db.flush()
        await self._renumber()
        await self.db.commit()

    async def reorder(self, ids: list[UUID]) -> list[RoutingRule]:
        """Persist a full reordering (ids highest priority first)."""
        existing = {rule.id for rule in await self.list_rules()}
        if set(ids) != existing or len(ids) != len(existing):
            raise ValidationException(
                "The reorder payload must contain every rule exactly once.",
                code="ROUTING_INVALID_ORDER",
            )
        rules_by_id = {rule.id: rule for rule in await self.list_rules()}
        for position, rule_id in enumerate(ids, start=1):
            rules_by_id[rule_id].priority = position
        await self.db.flush()
        await self.db.commit()
        return await self.list_rules()

    async def resolve_model(self, request_type: str) -> str | None:
        """Model to run for ``request_type``, or ``None`` for default resolution.

        Never returns a model that is not allowed to run: disabled catalog
        entries are skipped so the existing chat allow-list still holds.
        """
        allowed = await self._allowed_models()
        result = await self.db.execute(
            select(RoutingRule)
            .where(
                RoutingRule.is_active.is_(True),
                RoutingRule.request_type == request_type,
            )
            .order_by(RoutingRule.priority.asc())
        )
        for rule in result.scalars().all():
            if rule.primary_model in allowed:
                return rule.primary_model
            if rule.fallback_model and rule.fallback_model in allowed:
                return rule.fallback_model
        return None

    async def _allowed_models(self) -> set[str]:
        """Names chat is currently allowed to run (mirrors the chat allow-list)."""
        names = await self.db.execute(
            select(ModelConfig.name).where(ModelConfig.is_active.is_(True))
        )
        allowed = {name for name in names.scalars().all() if name}
        if settings.ollama_default_model:
            allowed.add(settings.ollama_default_model)
        # Built-in fallback provider (chat_service.FALLBACK_MODEL).
        allowed.update(_BUILT_IN_MODELS)
        return allowed

    async def _get_or_404(self, rule_id: UUID) -> RoutingRule:
        result = await self.db.execute(
            select(RoutingRule).where(RoutingRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if rule is None:
            raise not_found("Routing rule", rule_id)
        return rule

    async def _assert_request_type_available(self, request_type: str) -> None:
        existing = await self.db.execute(
            select(RoutingRule).where(RoutingRule.request_type == request_type)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictException(
                f"A routing rule for '{request_type}' already exists.",
                code="ROUTING_TYPE_TAKEN",
            )

    async def _assert_model_exists(self, name: str, *, required: bool) -> None:
        """Validate a referenced model against the catalog (any status)."""
        code = "ROUTING_PRIMARY_UNKNOWN" if required else "ROUTING_FALLBACK_UNKNOWN"
        label = "Primary" if required else "Fallback"
        result = await self.db.execute(
            select(ModelConfig).where(ModelConfig.name == name)
        )
        if result.scalar_one_or_none() is None and name not in (
            settings.ollama_default_model,
            *_BUILT_IN_MODELS,
        ):
            raise ValidationException(
                f"{label} model '{name}' does not exist in the model catalog.",
                code=code,
                details={"model": name},
            )

    async def _renumber(self) -> None:
        """Compact priorities to 1..N after a delete."""
        rules = await self.list_rules()
        for position, rule in enumerate(rules, start=1):
            rule.priority = position
        await self.db.flush()
