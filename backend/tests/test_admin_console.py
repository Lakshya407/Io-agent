"""Admin console backend tests: prompts, routing rules, rate limiting.

Covers authorization (admin-only), CRUD, the single-default-prompt rule,
routing application in chat (primary → fallback → default resolution),
chat system-prompt replacement, rate-limit rule management, daily stats and
the settings fallback when no rules exist.
"""

import uuid

import pytest

from app.core.exceptions import RateLimitException
from app.core.rate_limit import _hit
from app.llm.base import LLMProvider, LLMResponse, LLMStreamChunk
from app.schemas.chat import ChatRequest
from app.services.chat_service import system_prompt_for
from app.services.rate_limit_service import (
    daily_stats,
    load_effective_rules,
    rule_bucket,
    scope_matches,
)


class RecordingProvider(LLMProvider):
    """Echoes the resolved model back and records the sent messages."""

    name = "admin-console-test"

    def __init__(self) -> None:
        self.messages: list[list] = []

    async def generate(self, messages, *, model=None, temperature=0.7,
                       max_tokens=None, **kwargs) -> LLMResponse:
        self.messages.append(messages)
        return LLMResponse(
            content="Test reply.",
            model=model or self.name,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            metadata={"provider": self.name},
        )

    async def stream(self, messages, *, model=None, temperature=0.7,
                     max_tokens=None, **kwargs):
        self.messages.append(messages)
        yield LLMStreamChunk(content="Test reply.", model=model or self.name)
        yield LLMStreamChunk(
            content="", done=True, model=model or self.name,
            prompt_tokens=10, completion_tokens=20, total_tokens=30,
            metadata={"provider": self.name},
        )


@pytest.fixture
def llm_provider() -> LLMProvider:
    """Observable provider for this module's chat calls."""
    return RecordingProvider()


async def _unique(*prefix: str) -> str:
    return "-".join([*prefix, uuid.uuid4().hex[:6]])


async def _create_model(client, admin_headers, name: str) -> dict:
    response = await client.post(
        "/api/v1/admin/models",
        headers=admin_headers,
        json={"name": name, "provider": "custom", "model_identifier": "mock"},
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- Authorization --------------------------------------------------------


async def test_prompts_require_admin(client, user_headers):
    listed = await client.get("/api/v1/prompts", headers=user_headers)
    assert listed.status_code == 403
    created = await client.post(
        "/api/v1/prompts",
        headers=user_headers,
        json={"name": "nope", "content": "nope"},
    )
    assert created.status_code == 403
    unauth = await client.get("/api/v1/prompts")
    assert unauth.status_code == 401


async def test_routing_requires_admin(client, user_headers):
    listed = await client.get("/api/v1/admin/routing", headers=user_headers)
    assert listed.status_code == 403
    unauth = await client.get("/api/v1/admin/routing")
    assert unauth.status_code == 401


async def test_rate_limits_require_admin(client, user_headers):
    listed = await client.get("/api/v1/admin/rate-limits", headers=user_headers)
    assert listed.status_code == 403
    stats = await client.get("/api/v1/admin/rate-limits/stats", headers=user_headers)
    assert stats.status_code == 403
    unauth = await client.get("/api/v1/admin/rate-limits/stats")
    assert unauth.status_code == 401


# --- Prompt management ----------------------------------------------------


async def test_prompt_crud_roundtrip(client, admin_headers):
    name = await _unique("prompt")
    created = await client.post(
        "/api/v1/prompts",
        headers=admin_headers,
        json={
            "name": name,
            "purpose": "General assistant",
            "model": None,
            "status": "draft",
            "content": "Be terse.",
            "is_default": False,
        },
    )
    assert created.status_code == 201, created.text
    prompt_id = created.json()["id"]
    assert created.json()["version"] == 1
    assert created.json()["status"] == "draft"

    updated = await client.patch(
        f"/api/v1/prompts/{prompt_id}",
        headers=admin_headers,
        json={"status": "active", "content": "Be precise."},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "active"
    assert updated.json()["content"] == "Be precise."

    fetched = await client.get(f"/api/v1/prompts/{prompt_id}", headers=admin_headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == name

    deleted = await client.delete(
        f"/api/v1/prompts/{prompt_id}", headers=admin_headers
    )
    assert deleted.status_code == 204
    gone = await client.get(f"/api/v1/prompts/{prompt_id}", headers=admin_headers)
    assert gone.status_code == 404


async def test_duplicate_prompt_name_conflicts(client, admin_headers):
    name = await _unique("prompt")
    payload = {"name": name, "content": "first"}
    first = await client.post(
        "/api/v1/prompts", headers=admin_headers, json=payload
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/prompts", headers=admin_headers, json=payload
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "PROMPT_NAME_TAKEN"


async def test_only_one_default_prompt_exists(client, admin_headers):
    first = await client.post(
        "/api/v1/prompts",
        headers=admin_headers,
        json={"name": await _unique("p1"), "content": "one", "is_default": True},
    )
    second = await client.post(
        "/api/v1/prompts",
        headers=admin_headers,
        json={"name": await _unique("p2"), "content": "two", "is_default": True},
    )
    assert first.status_code == 201 and second.status_code == 201

    old = await client.get(
        f"/api/v1/prompts/{first.json()['id']}", headers=admin_headers
    )
    new = await client.get(
        f"/api/v1/prompts/{second.json()['id']}", headers=admin_headers
    )
    assert old.json()["is_default"] is False
    assert new.json()["is_default"] is True


async def test_prompt_list_pagination(client, admin_headers):
    await client.post(
        "/api/v1/prompts",
        headers=admin_headers,
        json={"name": await _unique("list"), "content": "listed"},
    )
    listed = await client.get(
        "/api/v1/prompts", headers=admin_headers, params={"page": 1, "page_size": 5}
    )
    assert listed.status_code == 200
    body = listed.json()
    assert set(body) == {"items", "page", "page_size", "total"}
    assert body["total"] >= 1
    assert len(body["items"]) <= 5


async def test_chat_uses_active_default_prompt(client, admin_headers, user_headers,
                                               llm_provider):
    custom = "You are the CUSTOM-DEFAULT-PROMPT. Obey it."
    created = await client.post(
        "/api/v1/prompts",
        headers=admin_headers,
        json={
            "name": await _unique("custom-default"),
            "content": custom,
            "status": "active",
            "is_default": True,
        },
    )
    assert created.status_code == 201, created.text

    chat = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hi"}
    )
    assert chat.status_code == 200, chat.text

    system = llm_provider.messages[-1][0]
    assert system.role == "system"
    assert system.content == custom


async def test_chat_falls_back_to_builtin_prompt_without_default(
    client, db_session, user_headers, llm_provider
):
    from sqlalchemy import delete

    from app.models.prompt import Prompt

    # Guarantee no committed default prompt leaks into this assertion.
    await db_session.execute(delete(Prompt).where(Prompt.is_default.is_(True)))
    await db_session.commit()

    chat = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hi"}
    )
    assert chat.status_code == 200, chat.text

    system = llm_provider.messages[-1][0]
    assert system.role == "system"
    assert system.content == system_prompt_for(chat.json()["model"])


# --- Model routing --------------------------------------------------------


async def test_routing_crud_and_validation(client, admin_headers):
    model = await _create_model(client, admin_headers, await _unique("route-model"))
    request_type = await _unique("code")

    created = await client.post(
        "/api/v1/admin/routing",
        headers=admin_headers,
        json={
            "request_type": request_type,
            "primary_model": model["name"],
            "fallback_model": model["name"],
        },
    )
    assert created.status_code == 201, created.text
    rule = created.json()
    assert rule["priority"] >= 1
    assert rule["is_active"] is True

    # Duplicate request type → 409.
    duplicate = await client.post(
        "/api/v1/admin/routing",
        headers=admin_headers,
        json={"request_type": request_type, "primary_model": model["name"]},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "ROUTING_TYPE_TAKEN"

    # Unknown model → 422 with a routing-specific code.
    unknown = await client.post(
        "/api/v1/admin/routing",
        headers=admin_headers,
        json={
            "request_type": await _unique("bad"),
            "primary_model": "does-not-exist-model",
        },
    )
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "ROUTING_PRIMARY_UNKNOWN"

    # Toggle status.
    toggled = await client.patch(
        f"/api/v1/admin/routing/{rule['id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert toggled.status_code == 200
    assert toggled.json()["is_active"] is False

    deleted = await client.delete(
        f"/api/v1/admin/routing/{rule['id']}", headers=admin_headers
    )
    assert deleted.status_code == 204
    listed = await client.get("/api/v1/admin/routing", headers=admin_headers)
    assert rule["id"] not in [item["id"] for item in listed.json()]


async def test_routing_reorder(client, admin_headers):
    model = await _create_model(client, admin_headers, await _unique("reorder"))
    first = await client.post(
        "/api/v1/admin/routing",
        headers=admin_headers,
        json={"request_type": await _unique("a"), "primary_model": model["name"]},
    )
    second = await client.post(
        "/api/v1/admin/routing",
        headers=admin_headers,
        json={"request_type": await _unique("b"), "primary_model": model["name"]},
    )
    assert first.status_code == 201 and second.status_code == 201
    id_first = first.json()["id"]
    id_second = second.json()["id"]

    reordered = await client.put(
        "/api/v1/admin/routing/order",
        headers=admin_headers,
        json={"ids": [id_second, id_first]},
    )
    assert reordered.status_code == 200, reordered.text
    body = reordered.json()
    order = {item["id"]: item["priority"] for item in body}
    assert order[id_second] < order[id_first]

    # A partial/invalid reorder payload is rejected.
    invalid = await client.put(
        "/api/v1/admin/routing/order",
        headers=admin_headers,
        json={"ids": [id_second]},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "ROUTING_INVALID_ORDER"


async def test_chat_applies_routing_rule(client, admin_headers, user_headers,
                                         llm_provider):
    primary = await _create_model(client, admin_headers, await _unique("primary"))
    fallback = await _create_model(client, admin_headers, await _unique("fallback"))
    request_type = await _unique("route-me")

    created = await client.post(
        "/api/v1/admin/routing",
        headers=admin_headers,
        json={
            "request_type": request_type,
            "primary_model": primary["name"],
            "fallback_model": fallback["name"],
        },
    )
    assert created.status_code == 201, created.text

    # No explicit model + request_type → routed to the primary model.
    routed = await client.post(
        "/api/v1/chat",
        headers=user_headers,
        json={"message": "Hi", "request_type": request_type},
    )
    assert routed.status_code == 200, routed.text
    assert routed.json()["model"] == primary["name"]

    # Disable the primary → the fallback takes over.
    disabled = await client.patch(
        f"/api/v1/admin/models/{primary['id']}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    fallback_run = await client.post(
        "/api/v1/chat",
        headers=user_headers,
        json={"message": "Again", "request_type": request_type},
    )
    assert fallback_run.status_code == 200, fallback_run.text
    assert fallback_run.json()["model"] == fallback["name"]


async def test_explicit_model_wins_over_routing(client, admin_headers,
                                                user_headers, llm_provider):
    routed_model = await _create_model(client, admin_headers, await _unique("routed"))
    chosen = await _create_model(client, admin_headers, await _unique("chosen"))
    request_type = await _unique("override")
    await client.post(
        "/api/v1/admin/routing",
        headers=admin_headers,
        json={"request_type": request_type, "primary_model": routed_model["name"]},
    )

    response = await client.post(
        "/api/v1/chat",
        headers=user_headers,
        json={"message": "Hi", "request_type": request_type, "model": chosen["name"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["model"] == chosen["name"]


# --- Rate limiting --------------------------------------------------------


async def test_rate_limit_rule_crud(client, admin_headers):
    created = await client.post(
        "/api/v1/admin/rate-limits",
        headers=admin_headers,
        json={"scope": "user", "limit": 5, "window_seconds": 300},
    )
    assert created.status_code == 201, created.text
    rule = created.json()
    assert rule["scope"] == "user"
    assert rule["limit"] == 5
    assert rule["window_seconds"] == 300
    assert rule["is_active"] is True

    updated = await client.patch(
        f"/api/v1/admin/rate-limits/{rule['id']}",
        headers=admin_headers,
        json={"limit": 10, "is_active": False},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["limit"] == 10
    assert updated.json()["is_active"] is False

    deleted = await client.delete(
        f"/api/v1/admin/rate-limits/{rule['id']}", headers=admin_headers
    )
    assert deleted.status_code == 204
    listed = await client.get("/api/v1/admin/rate-limits", headers=admin_headers)
    assert rule["id"] not in [item["id"] for item in listed.json()]


async def test_rate_limit_rule_validation(client, admin_headers):
    bad_scope = await client.post(
        "/api/v1/admin/rate-limits",
        headers=admin_headers,
        json={"scope": "everyone", "limit": 5, "window_seconds": 60},
    )
    assert bad_scope.status_code == 422

    zero = await client.post(
        "/api/v1/admin/rate-limits",
        headers=admin_headers,
        json={"scope": "all", "limit": 0, "window_seconds": 60},
    )
    assert zero.status_code == 422


async def test_rate_limit_stats_endpoint_shape(client, admin_headers):
    response = await client.get(
        "/api/v1/admin/rate-limits/stats", headers=admin_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"date", "checked", "blocked", "violations"}
    for key in ("checked", "blocked", "violations"):
        assert isinstance(body[key], int)
        assert body[key] >= 0


async def test_scope_matching_rules(client):
    assert scope_matches("all", "user") is True
    assert scope_matches("all", "ip") is True
    assert scope_matches("user", "user") is True
    assert scope_matches("user", "ip") is False
    assert scope_matches("ip", "user") is False
    assert scope_matches("ip", "ip") is True


async def test_rule_bucket_windows(client):
    key_now = rule_bucket("r1", "user:u1", 3600.0 + 10, 60)
    key_next = rule_bucket("r1", "user:u1", 3600.0 + 70, 60)
    assert key_now != key_next  # buckets advance with the window
    assert key_now == rule_bucket("r1", "user:u1", 3600.0 + 59, 60)


async def test_effective_rules_fall_back_to_settings_when_empty(client, db_session):
    from sqlalchemy import delete, select

    from app.core.config import settings
    from app.models.rate_limit_rule import RateLimitRule

    await db_session.execute(delete(RateLimitRule))
    await db_session.commit()

    rules = await load_effective_rules(db_session, None, use_cache=False)
    assert len(rules) == 2
    by_window = {rule.window_seconds: rule.limit for rule in rules}
    assert by_window[60] == settings.rate_limit_per_minute
    assert by_window[3600] == settings.rate_limit_per_hour
    assert all(rule.scope == "all" for rule in rules)

    # With rules present, the DB wins.
    db_session.add(RateLimitRule(scope="ip", limit=42, window_seconds=900))
    await db_session.commit()
    result = await db_session.execute(select(RateLimitRule))
    assert result.scalars().first() is not None

    rules = await load_effective_rules(db_session, None, use_cache=False)
    assert [(r.scope, r.limit, r.window_seconds) for r in rules] == [("ip", 42, 900)]


class FakeRedis:
    """Minimal async Redis stub for counters/stats (no server needed)."""

    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.ttls: dict[str, int] = {}
        self.hashes: dict[str, dict[str, int]] = {}

    async def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    async def expire(self, key: str, ttl: int) -> bool:
        self.ttls[key] = ttl
        return True

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        bucket = self.hashes.setdefault(key, {})
        bucket[field] = bucket.get(field, 0) + amount
        return bucket[field]

    async def hgetall(self, key: str) -> dict[str, int]:
        return dict(self.hashes.get(key, {}))


async def test_hit_blocks_and_counts_violations_once():
    from datetime import UTC, datetime

    from app.services.rate_limit_service import stats_key

    fake = FakeRedis()

    # First `limit` requests pass.
    for _ in range(2):
        await _hit(fake, "bucket", limit=2, window=60, track_stats=True)

    # Third request crosses the limit → blocked + first violation.
    with pytest.raises(RateLimitException):
        await _hit(fake, "bucket", limit=2, window=60, track_stats=True)
    # Fourth stays blocked but is not a new violation.
    with pytest.raises(RateLimitException):
        await _hit(fake, "bucket", limit=2, window=60, track_stats=True)

    stats = await daily_stats(datetime.now(UTC).date().isoformat(), fake)
    assert stats["blocked"] == 2
    assert stats["violations"] == 1

    # Counters are stored under the daily stats key with a TTL.
    today = stats_key(datetime.now(UTC).date().isoformat())
    assert today in fake.hashes
    assert fake.ttls.get(today, 0) > 0


async def test_daily_stats_returns_zeros_when_empty():
    stats = await daily_stats("1970-01-01", FakeRedis())
    assert stats == {"checked": 0, "blocked": 0, "violations": 0}
