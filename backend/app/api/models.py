"""Model router: list/read models (public to authenticated users).

Admin model management lives under /api/v1/admin/models. Endpoint contracts
are documented in docs/API.md.
"""

import time
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DBSession, PaginationParams
from app.core.logging import get_logger
from app.llm.base import LLMProviderError
from app.llm.ollama import OllamaProvider, _matches_model
from app.schemas.common import PaginatedResponse
from app.schemas.model import ModelOut, OllamaModelOut, OllamaModelsResponse
from app.services.model_service import ModelService

router = APIRouter(tags=["models"])
logger = get_logger(__name__)

# Cache Ollama's installed-model list so the UI (and admin status column)
# does not hammer Ollama on every render. 30s TTL, process-local.
_OLLAMA_CACHE: dict[str, object] = {"names": [], "at": 0.0}
_OLLAMA_CACHE_TTL = 30.0


async def _installed_names() -> list[str] | None:
    """Installed Ollama models, or ``None`` when Ollama is unreachable."""
    now = time.monotonic()
    cached_at = float(_OLLAMA_CACHE.get("at") or 0.0)
    if now - cached_at < _OLLAMA_CACHE_TTL and cached_at > 0:
        return list(_OLLAMA_CACHE["names"])  # type: ignore[arg-type]
    try:
        names = await OllamaProvider().list_models()
    except LLMProviderError as exc:
        logger.warning("Ollama model discovery failed: %s", exc)
        return None
    _OLLAMA_CACHE["names"] = names
    _OLLAMA_CACHE["at"] = now
    return names


@router.get(
    "",
    response_model=PaginatedResponse[ModelOut],
    summary="List available models",
    operation_id="models_list",
)
async def list_models(
    current_user: CurrentUser,
    db: DBSession,
    pagination: PaginationParams,
    active_only: bool = Query(
        True, description="Set to false to include disabled models"
    ),
    include_availability: bool = Query(
        False,
        description="Include local Ollama availability per model (cached)",
    ),
) -> PaginatedResponse[ModelOut]:
    """Return the catalog of models the platform can route to."""
    models, total = await ModelService(db).list_models(
        offset=pagination.offset,
        limit=pagination.page_size,
        active_only=active_only,
    )
    installed: list[str] | None = None
    if include_availability:
        installed = await _installed_names()
    items: list[ModelOut] = []
    for m in models:
        out = ModelOut.model_validate(m)
        if include_availability:
            if str(m.provider) == "ollama" and installed is not None:
                ident = m.model_identifier or m.name
                out.available = any(
                    _matches_model(name, ident) for name in installed
                )
            else:
                out.available = None
        items.append(out)
    return PaginatedResponse[ModelOut](
        items=items,
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get(
    "/ollama",
    response_model=OllamaModelsResponse,
    summary="List models installed on the Ollama instance",
    operation_id="models_ollama",
)
async def list_ollama_models(current_user: CurrentUser) -> OllamaModelsResponse:
    """Discover the models available on the configured Ollama instance.

    Read-only discovery for administrators (e.g. when deciding which model to
    add to the catalog). Chat requests may only use catalogued models — this
    list does not grant access to run them.
    """
    provider = OllamaProvider()
    try:
        installed = await provider.list_models()
    except LLMProviderError as exc:
        logger.warning("Ollama model discovery failed: %s", exc)
        installed = []
    return OllamaModelsResponse(
        models=[OllamaModelOut(name=name) for name in installed],
        default_model=provider.default_model or None,
    )


@router.get(
    "/{model_id}",
    response_model=ModelOut,
    summary="Get a model",
    operation_id="models_get",
)
async def get_model(
    model_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ModelOut:
    """Return a single model configuration."""
    model = await ModelService(db).get_model(model_id)
    return ModelOut.model_validate(model)


__all__ = ["router"]
