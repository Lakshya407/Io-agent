"""Streaming chat API tests (Phase 2: SSE + Phase 3: model validation).

All LLM I/O is mocked — no live Ollama is contacted. SSE responses are read
as raw text and parsed into ``(event, data)`` frames.
"""

import json
import uuid

import pytest

from app.llm.base import LLMProvider, LLMResponse, LLMStreamChunk, LLMUnavailableError
from app.models.conversation import Conversation
from app.schemas.chat import ChatMessage
from tests.conftest import _create_user, _unique_email


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    """Parse raw SSE text into ``(event, data)`` frames."""
    frames: list[tuple[str, dict]] = []
    event: str | None = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and event is not None:
            frames.append((event, json.loads(line.split(":", 1)[1].strip())))
            event = None
    return frames


class StreamProvider(LLMProvider):
    """Deterministic streaming provider for tests."""

    name = "stream-test"

    def __init__(
        self,
        chunks: list[str] | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.chunks = chunks if chunks is not None else ["Hello", " world"]
        self.error = error
        self.calls: list[dict] = []

    async def generate(self, messages, **kwargs) -> LLMResponse:
        content = "".join(self.chunks)
        return LLMResponse(
            content=content, model=kwargs.get("model") or self.name,
            prompt_tokens=5, completion_tokens=7, total_tokens=12,
            metadata={"provider": self.name},
        )

    async def stream(self, messages, **kwargs):
        self.calls.append({"messages": list(messages), "model": kwargs.get("model")})
        if self.error is not None:
            raise self.error
        for piece in self.chunks:
            yield LLMStreamChunk(content=piece, model="test-model")
        yield LLMStreamChunk(
            content="", done=True, model="test-model",
            prompt_tokens=5, completion_tokens=7, total_tokens=12,
        )


@pytest.fixture
def llm_provider() -> StreamProvider:
    return StreamProvider()


async def test_stream_unauthenticated_rejected(client):
    response = await client.post("/api/v1/chat/stream", json={"message": "Hi"})
    assert response.status_code == 401


async def test_stream_unknown_conversation_404(client, user_headers):
    # Ownership is validated before the SSE response starts → clean 404.
    response = await client.post(
        "/api/v1/chat/stream",
        headers=user_headers,
        json={"message": "Hi", "conversation_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_stream_success_event_format(client, user_headers, llm_provider):
    response = await client.post(
        "/api/v1/chat/stream", headers=user_headers, json={"message": "Hello"}
    )
    assert response.status_code == 200, response.text
    assert "text/event-stream" in response.headers["content-type"]
    frames = _parse_sse(response.text)
    events = [e for e, _ in frames]
    assert "message_start" in events
    assert "token" in events
    assert "message_complete" in events
    assert "activity" in events
    # Tokens concatenate to the full reply in ONE logical message.
    tokens = [d["content"] for e, d in frames if e == "token"]
    assert "".join(tokens) == "Hello world"
    complete = next(d for e, d in frames if e == "message_complete")
    assert complete["usage"]["total_tokens"] == 12
    start = next(d for e, d in frames if e == "message_start")
    assert start["conversation_id"]
    assert complete["conversation_id"] == start["conversation_id"]


async def test_stream_persists_messages(client, user_headers):
    response = await client.post(
        "/api/v1/chat/stream", headers=user_headers, json={"message": "Hello"}
    )
    frames = _parse_sse(response.text)
    start = next(d for e, d in frames if e == "message_start")
    cid = start["conversation_id"]
    messages = await client.get(
        f"/api/v1/conversations/{cid}/messages", headers=user_headers
    )
    assert messages.status_code == 200
    roles = [m["role"] for m in messages.json()["items"]]
    assert roles == ["user", "assistant"]
    assistant = next(m for m in messages.json()["items"] if m["role"] == "assistant")
    assert assistant["content"] == "Hello world"
    # Exactly one assistant row — never one row per token.
    assert sum(1 for m in messages.json()["items"] if m["role"] == "assistant") == 1


async def test_stream_cannot_use_other_users_conversation(
    client, db_session, user_headers, llm_provider
):
    other_user = await _create_user(db_session, email=_unique_email())
    other = Conversation(user_id=other_user.id, title="Not yours")
    db_session.add(other)
    await db_session.commit()

    response = await client.post(
        "/api/v1/chat/stream",
        headers=user_headers,
        json={"message": "Hi", "conversation_id": str(other.id)},
    )
    assert response.status_code == 404
    assert llm_provider.calls == []


async def test_stream_provider_outage_yields_error(client, user_headers, llm_provider):
    llm_provider.error = LLMUnavailableError("connection refused")
    response = await client.post(
        "/api/v1/chat/stream", headers=user_headers, json={"message": "Hello"}
    )
    assert response.status_code == 200
    frames = _parse_sse(response.text)
    assert any(e == "error" for e, _ in frames)
    err = next(d for e, d in frames if e == "error")
    assert "unavailable" in err["message"].lower()


async def test_stream_rejects_disabled_model(client, admin_headers, user_headers):
    name = f"stream-disabled-{uuid.uuid4().hex[:6]}"
    create = await client.post(
        "/api/v1/admin/models", headers=admin_headers,
        json={"name": name, "provider": "custom", "model_identifier": "mock"},
    )
    model_id = create.json()["id"]
    await client.patch(
        f"/api/v1/admin/models/{model_id}/status",
        headers=admin_headers, json={"is_active": False},
    )
    response = await client.post(
        "/api/v1/chat/stream", headers=user_headers,
        json={"message": "Hi", "model": name},
    )
    assert response.status_code == 200
    frames = _parse_sse(response.text)
    assert any(e == "error" for e, _ in frames)
