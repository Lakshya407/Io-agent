"""Phase 9 usage-tracking tests.

Covers: usage record creation, token calculation (actual vs estimated),
successful/failed/cancelled request tracking, allowance enforcement
(monthly, daily, disabled), admin authorization, user isolation and the
usage API responses.
"""

import uuid

import pytest
from sqlalchemy import select

from app.llm.base import LLMProvider, LLMResponse, LLMStreamChunk, LLMUnavailableError
from app.models.usage import UsageAllowance, UsageRecord
from app.models.user import User
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.chat_service import ChatService
from tests.conftest import _create_user, _login, _unique_email


class UsageRecordingProvider(LLMProvider):
    """Provider with a call log so tests can prove the LLM was (not) hit."""

    name = "usage-test"

    def __init__(
        self,
        content: str = "Usage test reply.",
        error: BaseException | None = None,
        prompt_tokens: int = 10,
        completion_tokens: int = 20,
    ) -> None:
        self.content = content
        self.error = error
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.calls: list[dict[str, object]] = []

    async def generate(self, messages, *, model=None, temperature=0.7,
                       max_tokens=None, **kwargs) -> LLMResponse:
        self.calls.append({"model": model})
        if self.error is not None:
            raise self.error
        return LLMResponse(
            content=self.content,
            model=model or self.name,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.prompt_tokens + self.completion_tokens,
            metadata={"provider": self.name},
        )

    async def stream(self, messages, *, model=None, temperature=0.7,
                     max_tokens=None, **kwargs):
        self.calls.append({"model": model})
        if self.error is not None:
            raise self.error
        for piece in ("Usage", " stream", " reply"):
            yield LLMStreamChunk(content=piece, model=model or self.name)
        yield LLMStreamChunk(
            content="", done=True, model=model or self.name,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.prompt_tokens + self.completion_tokens,
            metadata={"provider": self.name},
        )


@pytest.fixture
def llm_provider() -> LLMProvider:
    """Suite-wide override: observable provider for every chat call."""
    return UsageRecordingProvider()


async def _user_id(client, headers) -> uuid.UUID:
    me = await client.get("/api/v1/users/me", headers=headers)
    return uuid.UUID(me.json()["id"])


async def _records(db_session, user_id) -> list[UsageRecord]:
    result = await db_session.execute(
        select(UsageRecord)
        .where(UsageRecord.user_id == user_id)
        .order_by(UsageRecord.request_timestamp.asc())
    )
    return list(result.scalars().all())


async def _allowance(db_session, user_id) -> UsageAllowance:
    result = await db_session.execute(
        select(UsageAllowance).where(UsageAllowance.user_id == user_id)
    )
    return result.scalar_one()


# --- 1. Usage record creation + token calculation ------------------------


async def test_completed_request_creates_usage_record(
    client, db_session, user_headers, llm_provider
):
    response = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    assert response.status_code == 200, response.text

    user_id = await _user_id(client, user_headers)
    records = await _records(db_session, user_id)
    assert len(records) == 1

    record = records[0]
    assert record.user_id == user_id
    assert record.conversation_id == uuid.UUID(response.json()["conversation_id"])
    assert record.message_id is not None
    assert record.model == response.json()["model"]
    assert record.provider == "usage-test"
    assert record.request_status == "completed"
    assert record.prompt_tokens == 10
    assert record.completion_tokens == 20
    assert record.total_tokens == 30
    assert record.is_estimated is False  # provider reported actual counts
    assert record.response_duration_ms is not None
    assert record.response_duration_ms >= 0
    assert record.error_info is None
    assert record.request_timestamp is not None


async def test_token_calculation_feeds_allowance(
    client, db_session, user_headers, llm_provider
):
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hi"})

    usage = await client.get("/api/v1/usage", headers=user_headers)
    assert usage.json()["tokens_used"] == 30  # 10 prompt + 20 completion
    assert usage.json()["requests_used"] == 1


async def test_missing_token_counts_are_marked_estimated(
    client, db_session, user_headers
):
    """A provider that reports no counts → estimated tokens, clearly flagged."""
    user_id = await _user_id(client, user_headers)
    user = (
        await db_session.execute(select(User).where(User.id == user_id))
    ).scalar_one()
    service = ChatService(
        db_session,
        llm=UsageRecordingProvider(
            content="No counts in this reply.", prompt_tokens=0, completion_tokens=0
        ),
    )

    await service.chat(user, ChatRequest(message="Hello"))

    records = await _records(db_session, user_id)
    assert len(records) == 1
    record = records[0]
    assert record.is_estimated is True
    assert record.prompt_tokens > 0  # estimated from the sent text
    assert record.completion_tokens > 0  # estimated from the reply text
    assert record.total_tokens == record.prompt_tokens + record.completion_tokens

    # The estimated totals are what the allowance counted.
    allowance = await _allowance(db_session, user_id)
    assert allowance.tokens_used == record.total_tokens


async def test_estimated_tokens_when_provider_reports_zero(db_session):
    from app.services.usage_service import resolve_tokens

    prompt, completion, total, estimated = resolve_tokens(
        0, 0, prompt_text="x" * 40, completion_text="y" * 20
    )
    assert estimated is True
    assert prompt == 10
    assert completion == 5
    assert total == 15

    # Provider-reported counts are used as-is and never marked estimated.
    prompt, completion, total, estimated = resolve_tokens(7, 3)
    assert (prompt, completion, total, estimated) == (7, 3, 10, False)


# --- 2. Successful / failed / cancelled request tracking ------------------


async def test_stream_success_records_completed_usage(
    client, db_session, user_headers, llm_provider
):
    response = await client.post(
        "/api/v1/chat/stream", headers=user_headers, json={"message": "Hello"}
    )
    assert response.status_code == 200

    user_id = await _user_id(client, user_headers)
    records = await _records(db_session, user_id)
    assert len(records) == 1
    record = records[0]
    assert record.request_status == "completed"
    assert record.total_tokens == 30
    assert record.response_duration_ms is not None
    assert record.message_id is not None

    usage = await client.get("/api/v1/usage", headers=user_headers)
    assert usage.json()["requests_used"] == 1
    assert usage.json()["tokens_used"] == 30


async def test_failed_request_is_recorded_not_billed(
    client, db_session, user_headers
):
    """Provider outage → 503 + a ``failed`` record; quota is not consumed."""
    failing = UsageRecordingProvider(error=LLMUnavailableError("connection refused"))
    # Direct service call so the failing provider is guaranteed.
    user_id = await _user_id(client, user_headers)
    user = (
        await db_session.execute(select(User).where(User.id == user_id))
    ).scalar_one()
    service = ChatService(db_session, llm=failing)

    import pytest as _pytest

    with _pytest.raises(Exception):
        await service.chat(user, ChatRequest(message="Hello"))

    records = await _records(db_session, user_id)
    failed = [r for r in records if r.request_status == "failed"]
    assert len(failed) == 1
    assert failed[0].error_info is not None
    assert failed[0].error_info["code"] == "SERVICE_UNAVAILABLE"
    assert failed[0].response_duration_ms is not None

    # Failed requests must NOT consume the request allowance.
    allowance = await _allowance(db_session, user_id)
    assert allowance.requests_used == 0
    assert allowance.tokens_used == 0


async def test_cancelled_stream_is_recorded(client, db_session, user_headers):
    """Client abort (Stop) → ``cancelled`` record with partial usage."""
    user_id = await _user_id(client, user_headers)
    user = (
        await db_session.execute(select(User).where(User.id == user_id))
    ).scalar_one()
    service = ChatService(db_session, llm=UsageRecordingProvider())

    stream = service.stream_chat(user, ChatRequest(message="Hello"))
    async for item in stream:
        if item["event"] == "token":
            break
    await stream.aclose()

    records = await _records(db_session, user_id)
    cancelled = [r for r in records if r.request_status == "cancelled"]
    assert len(cancelled) == 1
    assert cancelled[0].response_duration_ms is not None

    # Cancelled requests count toward the request allowance (work was done).
    allowance = await _allowance(db_session, user_id)
    assert allowance.requests_used == 1


# --- 3. Allowance enforcement ---------------------------------------------


async def test_monthly_token_limit_blocks_before_llm_call(
    client, db_session, user_headers, llm_provider
):
    await client.get("/api/v1/usage", headers=user_headers)
    user_id = await _user_id(client, user_headers)
    allowance = await _allowance(db_session, user_id)
    allowance.monthly_token_limit = 1
    allowance.tokens_used = 1
    await db_session.commit()

    response = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "USAGE_LIMIT_EXCEEDED"
    assert "Monthly" in response.json()["error"]["message"]
    # The LLM must never be contacted for an over-quota request.
    assert llm_provider.calls == []
    # No usage record is created for a rejected request.
    assert await _records(db_session, user_id) == []


async def test_daily_token_limit_blocks_request(
    client, db_session, user_headers, llm_provider
):
    first = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    assert first.status_code == 200

    user_id = await _user_id(client, user_headers)
    allowance = await _allowance(db_session, user_id)
    allowance.daily_token_limit = 1  # already over after the first chat
    await db_session.commit()

    second = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Again"}
    )
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "USAGE_LIMIT_EXCEEDED"
    assert "Daily token" in second.json()["error"]["message"]
    assert len(llm_provider.calls) == 1  # only the first chat reached the LLM


async def test_daily_request_limit_blocks_request(
    client, db_session, user_headers, llm_provider
):
    await client.get("/api/v1/usage", headers=user_headers)
    user_id = await _user_id(client, user_headers)
    allowance = await _allowance(db_session, user_id)
    allowance.daily_request_limit = 1
    await db_session.commit()

    first = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Again"}
    )
    assert second.status_code == 429
    assert "Daily request" in second.json()["error"]["message"]
    assert len(llm_provider.calls) == 1


async def test_disabled_allowance_blocks_request(
    client, db_session, user_headers, llm_provider
):
    await client.get("/api/v1/usage", headers=user_headers)
    user_id = await _user_id(client, user_headers)
    allowance = await _allowance(db_session, user_id)
    allowance.is_enabled = False
    await db_session.commit()

    response = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    assert response.status_code == 429
    assert "disabled" in response.json()["error"]["message"].lower()
    assert llm_provider.calls == []


async def test_stream_allowance_enforced_before_generation(
    client, db_session, user_headers, llm_provider
):
    await client.get("/api/v1/usage", headers=user_headers)
    user_id = await _user_id(client, user_headers)
    allowance = await _allowance(db_session, user_id)
    allowance.is_enabled = False
    await db_session.commit()

    response = await client.post(
        "/api/v1/chat/stream", headers=user_headers, json={"message": "Hello"}
    )
    assert response.status_code == 200  # SSE contract: errors as events
    assert "USAGE_LIMIT_EXCEEDED" in response.text
    assert llm_provider.calls == []


async def test_admin_can_configure_daily_limits(client, db_session, admin_headers):
    user = await _create_user(db_session, email=_unique_email())
    response = await client.patch(
        f"/api/v1/admin/users/{user.id}/allowance",
        headers=admin_headers,
        json={
            "daily_token_limit": 500,
            "daily_request_limit": 10,
            "monthly_token_limit": 5000,
            "is_enabled": False,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["daily_token_limit"] == 500
    assert body["daily_request_limit"] == 10
    assert body["monthly_token_limit"] == 5000
    assert body["is_enabled"] is False

    # Explicit null clears a daily limit back to unlimited.
    cleared = await client.patch(
        f"/api/v1/admin/users/{user.id}/allowance",
        headers=admin_headers,
        json={"daily_token_limit": None, "is_enabled": True},
    )
    assert cleared.status_code == 200
    assert cleared.json()["daily_token_limit"] is None
    assert cleared.json()["is_enabled"] is True


# --- 4. Usage API responses ------------------------------------------------


async def test_usage_me_view(client, db_session, user_headers, llm_provider):
    # Fresh user: the view works before any usage exists.
    fresh = await client.get("/api/v1/usage/me", headers=user_headers)
    assert fresh.status_code == 200, fresh.text
    body = fresh.json()
    assert body["tokens_today"] == 0
    assert body["requests_today"] == 0
    assert body["tokens_this_month"] == 0
    assert body["is_allowed"] is True
    assert body["is_enabled"] is True
    assert body["daily_token_limit"] is None
    assert body["tokens_remaining_today"] is None  # no daily cap configured
    assert body["current_model"]  # a model is always resolvable

    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hello"})

    response = await client.get("/api/v1/usage/me", headers=user_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["tokens_today"] == 30
    assert body["requests_today"] == 1
    assert body["tokens_this_month"] == 30
    assert body["requests_this_month"] == 1
    assert body["tokens_remaining"] == body["monthly_token_limit"] - 30
    assert body["requests_remaining"] == body["monthly_request_limit"] - 1
    assert body["reset_at"] is not None


async def test_usage_summary_view(client, user_headers, llm_provider):
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hello"})

    response = await client.get("/api/v1/usage/summary", headers=user_headers)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "tokens_today",
        "requests_today",
        "tokens_this_month",
        "requests_this_month",
        "tokens_remaining",
        "requests_remaining",
        "current_model",
    }
    assert body["requests_today"] == 1
    assert body["tokens_this_month"] == 30
    assert body["current_model"]


# --- 5. User isolation ------------------------------------------------------


async def test_usage_me_is_isolated_between_users(
    client, db_session, user_headers, llm_provider
):
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hello"})

    other_email = _unique_email()
    await _create_user(db_session, email=other_email)
    other_headers = await _login(client, other_email, "test-password-123")

    mine = (await client.get("/api/v1/usage/me", headers=user_headers)).json()
    theirs = (await client.get("/api/v1/usage/me", headers=other_headers)).json()
    assert mine["tokens_this_month"] == 30
    assert theirs["tokens_this_month"] == 0
    assert theirs["requests_today"] == 0

    # History is isolated too.
    history = (
        await client.get("/api/v1/usage/history", headers=other_headers)
    ).json()
    assert history["total"] == 0


# --- 6. Admin authorization + analytics -------------------------------------


ADMIN_USAGE_ENDPOINTS = [
    "/api/v1/admin/usage/summary",
    "/api/v1/admin/usage/users",
    "/api/v1/admin/usage/models",
    "/api/v1/admin/usage/timeline",
]


async def test_admin_usage_endpoints_require_admin(client, user_headers):
    for path in ADMIN_USAGE_ENDPOINTS:
        response = await client.get(path, headers=user_headers)
        assert response.status_code == 403, f"{path}: {response.text}"
        assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_admin_usage_endpoints_unauthenticated(client):
    for path in ADMIN_USAGE_ENDPOINTS:
        response = await client.get(path)
        assert response.status_code == 401, f"{path}: {response.text}"


async def test_admin_usage_summary_and_breakdowns(
    client, db_session, admin_headers, user_headers, llm_provider
):
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hello"})
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hi"})
    user_id = await _user_id(client, user_headers)

    summary = await client.get(
        "/api/v1/admin/usage/summary",
        headers=admin_headers,
        params={"range": "today", "user_id": str(user_id)},
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["total_requests"] == 2
    assert body["successful_requests"] == 2
    assert body["failed_requests"] == 0
    assert body["cancelled_requests"] == 0
    assert body["total_tokens"] == 60
    assert body["prompt_tokens"] == 20
    assert body["completion_tokens"] == 40
    assert body["active_users"] == 1
    assert body["average_response_time_ms"] is not None

    by_user = await client.get(
        "/api/v1/admin/usage/users",
        headers=admin_headers,
        params={"range": "today", "user_id": str(user_id)},
    )
    assert by_user.status_code == 200
    rows = by_user.json()
    assert len(rows) == 1
    assert rows[0]["user_id"] == str(user_id)
    assert rows[0]["requests"] == 2
    assert rows[0]["total_tokens"] == 60

    by_model = await client.get(
        "/api/v1/admin/usage/models",
        headers=admin_headers,
        params={"range": "today", "user_id": str(user_id)},
    )
    assert by_model.status_code == 200
    model_rows = by_model.json()
    assert len(model_rows) == 1
    assert model_rows[0]["model"]
    assert model_rows[0]["requests"] == 2
    assert model_rows[0]["total_tokens"] == 60

    timeline = await client.get(
        "/api/v1/admin/usage/timeline",
        headers=admin_headers,
        params={"range": "today", "user_id": str(user_id)},
    )
    assert timeline.status_code == 200
    points = timeline.json()
    assert len(points) == 1
    assert points[0]["requests"] == 2
    assert points[0]["total_tokens"] == 60


async def test_admin_usage_custom_date_range_filters(
    client, db_session, admin_headers, user_headers, llm_provider
):
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hello"})
    user_id = await _user_id(client, user_headers)

    # A future window contains nothing.
    empty = await client.get(
        "/api/v1/admin/usage/summary",
        headers=admin_headers,
        params={
            "date_from": "2000-01-01",
            "date_to": "2000-01-02",
            "user_id": str(user_id),
        },
    )
    assert empty.status_code == 200
    assert empty.json()["total_requests"] == 0

    # Today's window contains the chat.
    today = await client.get(
        "/api/v1/admin/usage/summary",
        headers=admin_headers,
        params={"range": "today", "user_id": str(user_id)},
    )
    assert today.json()["total_requests"] == 1
