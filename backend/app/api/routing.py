"""Model routing router (admin-only).

CRUD over routing rules applied by ChatService when a request names no
explicit model. Endpoint contracts are documented in docs/API.md.
"""

from uuid import UUID

from fastapi import APIRouter, status

from app.core.dependencies import CurrentAdmin, DBSession
from app.schemas.routing import (
    RoutingRuleCreate,
    RoutingRuleOut,
    RoutingRuleOrder,
    RoutingRuleUpdate,
)
from app.services.routing_service import RoutingService

router = APIRouter(tags=["routing"])


@router.get(
    "",
    response_model=list[RoutingRuleOut],
    summary="List routing rules",
    operation_id="routing_list",
)
async def routing_list(
    admin: CurrentAdmin,
    db: DBSession,
) -> list[RoutingRuleOut]:
    """Every rule, highest priority first (admin only)."""
    rules = await RoutingService(db).list_rules()
    return [RoutingRuleOut.model_validate(rule) for rule in rules]


@router.post(
    "",
    response_model=RoutingRuleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a routing rule",
    operation_id="routing_create",
)
async def routing_create(
    admin: CurrentAdmin,
    db: DBSession,
    payload: RoutingRuleCreate,
) -> RoutingRuleOut:
    """Add a rule at the lowest priority (appended to the end)."""
    rule = await RoutingService(db).create_rule(payload)
    return RoutingRuleOut.model_validate(rule)


@router.put(
    "/order",
    response_model=list[RoutingRuleOut],
    summary="Reorder routing rules",
    operation_id="routing_reorder",
)
async def routing_reorder(
    admin: CurrentAdmin,
    db: DBSession,
    payload: RoutingRuleOrder,
) -> list[RoutingRuleOut]:
    """Persist a full reordering — every rule id exactly once, best first."""
    rules = await RoutingService(db).reorder(payload.ids)
    return [RoutingRuleOut.model_validate(rule) for rule in rules]


@router.patch(
    "/{rule_id}",
    response_model=RoutingRuleOut,
    summary="Update a routing rule",
    operation_id="routing_update",
)
async def routing_update(
    admin: CurrentAdmin,
    db: DBSession,
    rule_id: UUID,
    payload: RoutingRuleUpdate,
) -> RoutingRuleOut:
    """Partially update a rule (models are re-validated when changed)."""
    rule = await RoutingService(db).update_rule(rule_id, payload)
    return RoutingRuleOut.model_validate(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a routing rule",
    operation_id="routing_delete",
)
async def routing_delete(
    admin: CurrentAdmin,
    db: DBSession,
    rule_id: UUID,
) -> None:
    """Remove a rule and renumber the remainder (admin only)."""
    await RoutingService(db).delete_rule(rule_id)
