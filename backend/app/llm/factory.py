"""LLM provider factory.

The service layer asks for a provider by name and never knows which concrete
class it receives. Adding a provider (OpenAI, Anthropic, ...) means:

    1. implement ``app/llm/<provider>.py`` (see ``base.LLMProvider``),
    2. register it in ``_PROVIDERS`` below.

No other file in the application needs to change — least of all the chat API.
"""

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.llm.ollama import OllamaProvider

logger = get_logger(__name__)


def _providers() -> dict[str, type[LLMProvider]]:
    """Provider registry. Kept as a function so registration is lazy."""
    return {
        "mock": MockLLMProvider,
        "ollama": OllamaProvider,
    }


def get_llm_provider(provider_name: str | None = None) -> LLMProvider:
    """Return a fresh instance of the requested (or default) provider."""
    name = (provider_name or settings.llm_provider or "mock").strip().lower()
    factory = _providers().get(name)
    if factory is None:
        raise ValueError(
            f"Unknown LLM provider {name!r}. "
            f"Known providers: {', '.join(sorted(_providers()))}."
        )
    logger.debug("Instantiating LLM provider: %s", name)
    return factory()


__all__ = ["get_llm_provider"]
