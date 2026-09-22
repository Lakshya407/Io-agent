"""Ollama provider tests.

Every test drives the provider through an ``httpx.MockTransport`` so nothing
ever touches a real Ollama instance (the suite must not depend on a local
installation or network access).
"""

import json

import httpx
import pytest

from app.llm.base import (
    LLMEmptyResponseError,
    LLMModelNotFoundError,
    LLMProviderError,
    LLMResponse,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.ollama import OllamaProvider
from app.schemas.chat import ChatMessage, MessageRole

BASE_URL = "http://ollama.test"


def _messages() -> list[ChatMessage]:
    return [
        ChatMessage(role=MessageRole.USER, content="Explain Docker"),
    ]


def _chat_payload(
    *,
    content: str = "Docker packages software into containers.",
    model: str = "llama3.2",
    prompt_eval_count: int = 12,
    eval_count: int = 34,
    **extra: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": model,
        "created_at": "2026-09-21T00:00:00Z",
        "message": {"role": "assistant", "content": content},
        "done": True,
        "prompt_eval_count": prompt_eval_count,
        "eval_count": eval_count,
    }
    payload.update(extra)
    return payload


def _provider(
    handler: object, **kwargs: object
) -> OllamaProvider:
    return OllamaProvider(
        base_url=BASE_URL,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        **kwargs,
    )


def test_provider_reads_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Construction without explicit args falls back to configuration."""
    monkeypatch.setattr("app.llm.ollama.settings.ollama_base_url", "http://cfg:11434/")
    monkeypatch.setattr("app.llm.ollama.settings.ollama_default_model", "qwen2.5")
    monkeypatch.setattr("app.llm.ollama.settings.ollama_request_timeout", 42.0)

    provider = OllamaProvider(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    assert provider.base_url == "http://cfg:11434"  # trailing slash trimmed
    assert provider.default_model == "qwen2.5"
    assert provider.timeout == 42.0


async def test_generate_success_sends_expected_payload() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.read())
        return httpx.Response(200, json=_chat_payload())

    provider = _provider(handler)
    response = await provider.generate(
        _messages(), model="llama3.2", temperature=0.25, max_tokens=1024
    )

    assert isinstance(response, LLMResponse)
    assert response.content == "Docker packages software into containers."
    assert response.model == "llama3.2"
    assert response.prompt_tokens == 12
    assert response.completion_tokens == 34
    assert response.total_tokens == 46
    assert response.metadata["provider"] == "ollama"

    assert seen["url"] == f"{BASE_URL}/api/chat"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["model"] == "llama3.2"
    assert body["stream"] is False
    assert body["messages"] == [{"role": "user", "content": "Explain Docker"}]
    assert body["options"]["temperature"] == 0.25
    # Ollama's completion-length option is ``num_predict``.
    assert body["options"]["num_predict"] == 1024
    # The model is kept warm so later requests skip the reload penalty.
    assert body["keep_alive"] == "30m"


async def test_generate_uses_configured_default_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_payload())

    provider = _provider(handler, default_model="llama3.2")
    response = await provider.generate(_messages())

    assert response.model == "llama3.2"


async def test_generate_without_any_model_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.llm.ollama.settings.ollama_default_model", "")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_payload())

    provider = _provider(handler, default_model="")
    with pytest.raises(LLMModelNotFoundError):
        await provider.generate(_messages())


async def test_generate_strips_whitespace_only_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_payload(content="   "))

    provider = _provider(handler)
    with pytest.raises(LLMEmptyResponseError):
        await provider.generate(_messages(), model="llama3.2")


async def test_missing_message_field_raises_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"model": "llama3.2", "done": True})

    provider = _provider(handler)
    with pytest.raises(LLMEmptyResponseError):
        await provider.generate(_messages(), model="llama3.2")


async def test_unknown_model_returns_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404, json={"error": "model 'nope' not found, try pulling it first"}
        )

    provider = _provider(handler)
    with pytest.raises(LLMModelNotFoundError):
        await provider.generate(_messages(), model="nope")


@pytest.mark.parametrize(
    "exception, expected",
    [
        (httpx.ConnectTimeout, LLMUnavailableError),
        (httpx.ConnectError, LLMUnavailableError),
        (httpx.ReadTimeout, LLMTimeoutError),
        (httpx.WriteError, LLMProviderError),
    ],
)
async def test_transport_failures_map_to_provider_errors(
    exception: type[Exception], expected: type[LLMProviderError]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception("simulated transport failure")

    provider = _provider(handler)
    with pytest.raises(expected):
        await provider.generate(_messages(), model="llama3.2")


async def test_http_500_maps_to_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "internal ollama error"})

    provider = _provider(handler)
    with pytest.raises(LLMProviderError):
        await provider.generate(_messages(), model="llama3.2")


async def test_non_json_body_maps_to_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>not json</html>")

    provider = _provider(handler)
    with pytest.raises(LLMProviderError):
        await provider.generate(_messages(), model="llama3.2")


async def test_list_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/api/tags")
        return httpx.Response(
            200,
            json={
                "models": [
                    {"name": "llama3.2:latest", "size": 2000000000},
                    {"name": "qwen2.5:latest", "size": 1500000000},
                ]
            },
        )

    provider = _provider(handler)
    assert await provider.list_models() == ["llama3.2:latest", "qwen2.5:latest"]
    assert await provider.is_model_available("qwen2.5:latest") is True
    assert await provider.is_model_available("gpt-4o") is False


async def test_is_model_available_is_false_when_ollama_down() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _provider(handler)
    assert await provider.is_model_available("llama3.2") is False


async def test_health_check_healthy() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"models": [{"name": "llama3.2:latest"}]}
        )

    provider = _provider(handler, default_model="llama3.2:latest")
    result = await provider.health_check()

    assert result["status"] == "healthy"
    assert result["provider"] == "ollama"
    assert result["base_url"] == BASE_URL
    assert result["models"] == 1
    assert result["model"] == "llama3.2:latest"
    assert result["model_available"] is True


async def test_bare_model_name_matches_tagged_install() -> None:
    """``llama3.2`` is available when Ollama reports ``llama3.2:latest``."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"models": [{"name": "llama3.2:latest"}]}
        )

    provider = _provider(handler, default_model="llama3.2")
    assert await provider.is_model_available("llama3.2") is True
    result = await provider.health_check()
    assert result["model_available"] is True


async def test_health_check_reports_missing_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": []})

    provider = _provider(handler, default_model="llama3.2")
    result = await provider.health_check()

    assert result["status"] == "healthy"
    assert result["model_available"] is False


async def test_health_check_never_raises_when_down() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _provider(handler)
    result = await provider.health_check()

    assert result["status"] == "unavailable"
    assert result["provider"] == "ollama"
    assert result["base_url"] == BASE_URL
