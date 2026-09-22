"""Ollama LLM provider.

Talks to a locally (or privately) hosted Ollama instance over its HTTP API
only. The rest of the application never sees Ollama's response format: this
class converts it into the normalized :class:`~app.llm.base.LLMResponse`.

Ollama's HTTP endpoints used here:

    POST {base_url}/api/chat   non-streaming chat completion
    GET  {base_url}/api/tags   models installed on the instance

Endpoints, payload shape and error semantics are Ollama-specific and stay
inside this module — swapping providers means writing a new provider class,
not touching the service or API layers.
"""

import httpx

from app.core.config import settings
from app.llm.base import (
    LLMEmptyResponseError,
    LLMModelNotFoundError,
    LLMProvider,
    LLMProviderError,
    LLMResponse,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.schemas.chat import ChatMessage

# Ollama answers quickly once a model is loaded, but the first request for a
# model pulls/warm-loads it, so the connect window is short while the read
# window honours the full request timeout.
_CONNECT_TIMEOUT_SECONDS = 10.0


def _matches_model(installed: str, requested: str) -> bool:
    """Compare a model name against an installed Ollama model.

    Ollama reports installed models with an explicit tag (``llama3.2:latest``)
    but happily accepts the bare name for generation, so a missing tag is not
    an availability mismatch.
    """
    return installed == requested or installed == f"{requested}:latest"


class OllamaProvider(LLMProvider):
    """Ollama HTTP API adapter."""

    name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float | None = None,
        default_model: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = timeout or settings.ollama_request_timeout
        self.default_model = default_model or settings.ollama_default_model
        # ``transport`` is a test seam (httpx.MockTransport); in production it
        # is ``None`` and httpx uses the default network transport.
        self._transport = transport

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: object,
    ) -> LLMResponse:
        """Send the conversation to Ollama and return a normalized reply."""
        model = model or self.default_model
        if not model:
            raise LLMModelNotFoundError(
                "No model requested and no default model is configured."
            )

        payload: dict[str, object] = {
            "model": model,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in messages
            ],
            "stream": False,
            "options": {"temperature": temperature},
            # Keep the model in memory after this request. On CPU-only machines
            # reloading a model from disk costs tens of seconds, which would
            # dominate every response after Ollama's idle unload. Set to 0 (or
            # OLLAMA_KEEP_ALIVE=0) to disable.
            "keep_alive": settings.ollama_keep_alive,
        }
        if max_tokens is not None:
            # Ollama's name for the completion-length cap is ``num_predict``.
            payload["options"]["num_predict"] = max_tokens  # type: ignore[union-attr]

        data = await self._post("/api/chat", payload)

        content = (data.get("message") or {}).get("content")
        if not content or not content.strip():
            raise LLMEmptyResponseError(
                f"Ollama returned an empty response for model {model!r}."
            )

        response_model = str(data.get("model") or model)
        prompt_tokens = int(data.get("prompt_eval_count") or 0)
        completion_tokens = int(data.get("eval_count") or 0)
        return LLMResponse(
            content=content.strip(),
            model=response_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            metadata={"provider": self.name},
        )

    async def list_models(self) -> list[str]:
        """Return the names of the models installed on the Ollama instance."""
        data = await self._get("/api/tags")
        return [
            str(item["name"])
            for item in data.get("models", [])
            if item.get("name")
        ]

    async def is_model_available(self, model: str) -> bool:
        """True when ``model`` is installed on the Ollama instance."""
        try:
            installed = await self.list_models()
        except LLMProviderError:
            return False
        return any(_matches_model(name, model) for name in installed)

    async def health_check(self) -> dict[str, object]:
        """Reach out to Ollama and report availability for the health probe.

        Never raises — the caller (a health endpoint) always gets a payload it
        can serialize, even when Ollama is down.
        """
        payload: dict[str, object] = {
            "provider": self.name,
            "base_url": self.base_url,
        }
        try:
            installed = await self.list_models()
        except LLMProviderError as exc:
            payload["status"] = "unavailable"
            payload["error"] = type(exc).__name__
            return payload

        payload["status"] = "healthy"
        payload["models"] = len(installed)
        configured = self.default_model
        if configured:
            payload["model"] = configured
            payload["model_available"] = any(
                _matches_model(name, configured) for name in installed
            )
        return payload

    # --- internals -------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=_CONNECT_TIMEOUT_SECONDS),
            transport=self._transport,
        )

    async def _get(self, path: str) -> dict[str, object]:
        return await self._request("GET", path)

    async def _post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        return await self._request("POST", path, payload)

    async def _request(
        self, method: str, path: str, payload: dict[str, object] | None = None
    ) -> dict[str, object]:
        try:
            async with self._client() as client:
                response = await client.request(method, path, json=payload)
        except httpx.ConnectTimeout:
            raise LLMUnavailableError(
                f"Cannot connect to Ollama at {self.base_url} (connect timeout)."
            )
        except httpx.ConnectError as exc:
            raise LLMUnavailableError(
                f"Cannot connect to Ollama at {self.base_url}: {exc}"
            )
        except httpx.ReadTimeout:
            raise LLMTimeoutError(
                f"Ollama did not answer within {self.timeout:.0f}s "
                f"({self.base_url}{path})."
            )
        except httpx.HTTPError as exc:  # noqa: BLE001 - any other transport failure
            raise LLMProviderError(f"Ollama HTTP request failed: {exc}")

        if response.status_code == 404:
            # Ollama reports an unknown model with a 404 and a JSON ``error``.
            detail = ""
            try:
                detail = str((response.json() or {}).get("error", ""))
            except ValueError:
                pass
            raise LLMModelNotFoundError(
                f"Model not found on Ollama: {detail or 'unknown model'}"
            )
        if response.status_code >= 400:
            raise LLMProviderError(
                f"Ollama returned HTTP {response.status_code} for {path}."
            )

        try:
            return response.json()  # type: ignore[no-any-return]
        except ValueError:
            raise LLMProviderError("Ollama returned a non-JSON response.")


__all__ = ["OllamaProvider"]
