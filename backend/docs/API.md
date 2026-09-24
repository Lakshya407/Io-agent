# API Contract — AI Agent Platform Backend

Base URL: `http://localhost:8000` · API version prefix: `/api/v1`
Interactive docs: `/docs` · ReDoc: `/redoc` · OpenAPI JSON: `/openapi.json`

## Conventions

### Authentication

All endpoints except `/health*`, `POST /auth/register`, `POST /auth/login` and
`POST /auth/refresh` require a JWT bearer token:

```
Authorization: Bearer <access_token>
```

Tokens are obtained from `POST /api/v1/auth/login` (OAuth2 form) or
`POST /api/v1/auth/register`. Access tokens live 30 minutes (configurable),
refresh tokens 7 days. Admin-only endpoints additionally require the user's
role to be `admin`, otherwise a `403 FORBIDDEN` is returned.

### Error envelope

Every failing request returns a consistent body and never exposes internal
stack traces:

```json
{
  "success": false,
  "error": { "code": "USER_NOT_FOUND", "message": "User not found" },
  "request_id": "3b4b0888-73a7-48a4-b345-be77f640a2a"
}
```

Common status codes: `401 UNAUTHORIZED`, `403 FORBIDDEN`, `404 NOT_FOUND`,
`409 CONFLICT`, `422 VALIDATION_ERROR`, `429 USAGE_LIMIT_EXCEEDED` /
`RATE_LIMIT_EXCEEDED`, `503 SERVICE_UNAVAILABLE`, `500 INTERNAL_ERROR`. Every
response carries an `X-Request-ID` header (preserved when the client sends one).

### Pagination

Collection endpoints accept `?page=1&page_size=20` (max `page_size=100`) and
return:

```json
{ "items": [], "page": 1, "page_size": 20, "total": 100 }
```

---

## Health

### `GET /health` — liveness probe
- **Auth:** none · **Request:** none
- **Response 200:** `{"status": "ok"}`

### `GET /health/ready` — readiness probe
- **Auth:** none · **Request:** none
- **Response 200:** `{"status": "ok", "checks": {"postgres": "ok", "redis": "ok"}}`
- **Response 503:** `{"status": "degraded", "checks": {"postgres": "error: ...", "redis": "ok"}}`

### `GET /health/llm` — LLM provider probe
- **Auth:** none · **Request:** none
- Checks that the backend can reach the configured LLM provider (Ollama). It
  is separate from `/health/ready` on purpose: an unavailable LLM degrades chat
  but must not mark the whole service unhealthy.
- **Response 200:**
```json
{ "status": "healthy", "provider": "ollama", "base_url": "http://host.docker.internal:11434", "models": 1, "model": "llama3.2", "model_available": true }
```
- **Response 503:**
```json
{ "status": "unavailable", "provider": "ollama", "base_url": "http://host.docker.internal:11434", "error": "LLMUnavailableError" }
```

---

## Authentication

### `POST /api/v1/auth/register`
- **Auth:** none
- **Request:**
```json
{ "email": "user@example.com", "password": "strong-password", "name": "User" }
```
- **Response 201:** `{ "access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 1800 }`
- **Errors:** `409 EMAIL_ALREADY_REGISTERED`, `422` (weak/missing fields)

### `POST /api/v1/auth/login`
- **Auth:** none · **Request:** OAuth2 form (`username`, `password`)
- **Response 200:** same token pair as register
- **Errors:** `401 INVALID_CREDENTIALS` (identical for unknown email and wrong
  password — the endpoint cannot be used to enumerate accounts),
  `401 USER_DISABLED`

### `POST /api/v1/auth/refresh`
- **Auth:** none
- **Request:** `{ "refresh_token": "..." }`
- **Response 200:** a fresh token pair
- **Errors:** `401 TOKEN_EXPIRED` / `TOKEN_INVALID`, `401 USER_NOT_FOUND`,
  `401 USER_DISABLED`

### `GET /api/v1/auth/me`
- **Auth:** user
- **Response 200:** [`UserOut`](#userout)

---

## Chat

### `POST /api/v1/chat`
- **Auth:** user
- **Request:**
```json
{ "message": "Hello", "conversation_id": null, "model": null, "request_type": null }
```
  Omit `conversation_id` to start a new conversation; pass an existing one to
  continue it. `model` overrides the default model; it must be an active model
  in the catalog (or the configured default), otherwise `422
  MODEL_NOT_AVAILABLE` is returned — the frontend cannot run arbitrary models.
  `request_type` (e.g. `"Code"`, `"Summarize"`) selects a **routing rule** when
  no explicit `model` is given — see
  [`POST /admin/routing`](#post-apiv1adminrouting); an explicit `model` always
  wins, and routing can never bypass the active-model allow-list.
  Conversation history is loaded from PostgreSQL and sent to the provider with
  every request.
- **Response 200:**
```json
{
  "conversation_id": "2b7d2f97-9276-4eb8-bcc2-6d6aa21c2366",
  "message": { "role": "assistant", "content": "Docker packages applications into containers…" },
  "model": "llama3.2",
  "usage": { "prompt_tokens": 41, "completion_tokens": 128, "total_tokens": 169 }
}
```
  Records both messages and increments the caller's monthly usage.
- **Errors:** `404 NOT_FOUND` (unknown/non-owned conversation),
  `422 MODEL_NOT_AVAILABLE` (model is not catalogued/not installed),
  `429 USAGE_LIMIT_EXCEEDED` (monthly allowance exhausted),
  `503 SERVICE_UNAVAILABLE` (LLM provider unreachable, timed out or returned
  an empty response — the message is always
  *"AI service is currently unavailable. Please try again."*)

### `POST /api/v1/chat/stream` — streaming reply (SSE)
- **Auth:** user
- **Request:** same as `POST /api/v1/chat` (`message`, `conversation_id`,
  `model`, `request_type`)
- **Response 200:** `text/event-stream` with structured frames:
```
event: activity
data: {"stage": "started", "detail": "Request received"}

event: activity
data: {"stage": "model", "detail": "Using llama3.2", "model": "llama3.2", "provider": "ollama"}

event: message_start
data: {"message_id": "uuid", "conversation_id": "uuid", "model": "llama3.2"}

event: token
data: {"content": "Hello"}

event: token
data: {"content": " world"}

event: activity
data: {"stage": "completed", "detail": "Response generated"}

event: message_complete
data: {"message_id": "uuid", "conversation_id": "uuid", "model": "llama3.2", "status": "completed", "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12}}
```
- **Error frame:** `event: error` + `data: {"message": "AI service is currently unavailable."}`
- Client abort (Stop button → `AbortController.abort()`) preserves the
  partial reply server-side with `status="stopped"`. No auto-reconnect: a
  broken stream stops, keeps received content, and never resends the message.
- **Errors:** same codes as `POST /api/v1/chat`, plus `404 NOT_FOUND` for
  unknown/non-owned conversations (before the stream starts).

### `GET /api/v1/conversations`
- **Auth:** user · **Query:** pagination
- **Response 200:** paginated [`ConversationSummary`](#conversationsummary)

### `GET /api/v1/conversations/{conversation_id}`
- **Auth:** user
- **Response 200:** [`ConversationSummary`](#conversationsummary)
- **Errors:** `404 NOT_FOUND` (or a conversation owned by another user)

### `GET /api/v1/conversations/{conversation_id}/messages`
- **Auth:** user · **Query:** pagination
- **Response 200:** paginated [`MessageOut`](#messageout), oldest first
- **Errors:** `404 NOT_FOUND`

### `DELETE /api/v1/conversations/{conversation_id}`
- **Auth:** user
- **Response 204:** no content (cascades to messages)
- **Errors:** `404 NOT_FOUND`

---

## Users

### `GET /api/v1/users/me`  ·  `PUT /api/v1/users/me`
- **Auth:** user
- **PUT request:** `{ "name": "Renamed", "email": "new@example.com" }` (both optional)
- **Response 200:** [`UserOut`](#userout)
- **Errors:** `409 EMAIL_ALREADY_REGISTERED`

### `GET /api/v1/users` — list users (admin)
- **Auth:** admin · **Query:** pagination
- **Response 200:** paginated [`UserOut`](#userout) · **Errors:** `403 FORBIDDEN`

### `GET /api/v1/users/{user_id}` · `PATCH /api/v1/users/{user_id}` · `DELETE /api/v1/users/{user_id}`
- **Auth:** admin
- **PATCH request:** `{ "name": "...", "email": "...", "role": "admin", "is_active": false }` (all optional)
- **Response:** `UserOut` / `UserOut` / `204`
- **Errors:** `403 FORBIDDEN`, `404 NOT_FOUND`, `409 EMAIL_ALREADY_REGISTERED`

---

## Models

### `GET /api/v1/models` — list models
- **Auth:** user · **Query:** pagination, `active_only=true`,
  `include_availability=false`
- **Response 200:** paginated [`ModelOut`](#modelout). With
  `include_availability=true`, Ollama-catalogued models carry
  `available: true/false` (30s server-side cache over Ollama `/api/tags`;
  `null` for non-Ollama models or when Ollama is unreachable).

### `GET /api/v1/models/ollama` — list models installed on Ollama
- **Auth:** user
- **Response 200:** read-only discovery of the models available on the
  configured Ollama instance. Listing a model here does **not** make it usable
  for chat — only catalogued models may run.
```json
{ "models": [{ "name": "llama3.2:latest" }], "default_model": "llama3.2" }
```
- **Errors:** none (returns an empty list if Ollama is unreachable)

### `GET /api/v1/models/{model_id}`
- **Auth:** user · **Response 200:** [`ModelOut`](#modelout) · **Errors:** `404 NOT_FOUND`

---

## Tools

### `GET /api/v1/tools` — list tools
- **Auth:** user · **Query:** pagination, `active_only=true`
- **Response 200:** paginated [`ToolOut`](#toolout)

### `GET /api/v1/tools/{tool_id}`
- **Auth:** user · **Response 200:** [`ToolOut`](#toolout) · **Errors:** `404 NOT_FOUND`

---

## Usage

Usage is recorded per chat round in `usage_records` by `UsageService`
(`app/services/usage_service.py`) — route handlers never touch it. Every record
carries the user/conversation/message ids, model, provider, prompt/completion/
total tokens, `is_estimated`, timestamp, duration and a status of
`completed` / `failed` / `cancelled` (plus error details when relevant). Tokens
count toward billing for **any** status; the request quota is only consumed by
`completed` and `cancelled` rounds. If the provider reports no token counts the
value is estimated at ~4 characters per token and flagged `is_estimated`.

Allowances are checked **before** the LLM call (`429 USAGE_LIMIT_EXCEEDED`
otherwise), using Redis as a fast path with PostgreSQL as the source of truth.
A Redis failure is logged and falls back to PostgreSQL — it never blocks chat.
Recording a usage entry must never break a successful response; failures are
logged instead.

### `GET /api/v1/usage` — my allowance
- **Auth:** user
- **Response 200:** [`UsageOut`](#usageout)

### `GET /api/v1/usage/me` — my usage view
- **Auth:** user
- **Response 200:** [`UsageMeOut`](#usagemeout) — today's and this month's
  tokens/requests, remaining allowance (monthly + optional daily), the current
  model and whether the caller is currently allowed to send. Only ever the
  authenticated user's own numbers.

### `GET /api/v1/usage/summary` — compact personal summary
- **Auth:** user
- **Response 200:** [`UsageSummaryOut`](#usagesummaryout) — lighter variant of
  `/usage/me` (tokens/requests today and this month, remaining, current model)
  for cheap polling.

### `GET /api/v1/usage/history` — my aggregated usage
- **Auth:** user · **Query:** pagination, `model`, `provider`, `date_from`, `date_to`
- **Response 200:** paginated `UsageHistoryItem`:
```json
{ "items": [{ "period": "2026-09-17", "requests": 2, "tokens": 21 }], "page": 1, "page_size": 20, "total": 1 }
```
  Aggregation is performed by PostgreSQL; one chat round is counted once.

---

## Admin

All admin endpoints require an administrator (`403 FORBIDDEN` otherwise).
All mutations write an audit log entry (see `GET /admin/audit-logs`).

### `GET /api/v1/admin/dashboard`
- **Response 200:** [`DashboardStats`](#dashboardstats)

### `GET /api/v1/admin/users` · `GET /api/v1/admin/usage`
- **Query:** pagination
- **Response 200:** paginated `UserOut` / paginated `AdminUsageRow`

### `GET /api/v1/admin/usage/summary`
- **Auth:** admin · **Query:** `range`, `date_from`, `date_to`, `model`, `user_id`
- **Response 200:** [`AdminUsageSummary`](#adminusagesummary)

### `GET /api/v1/admin/usage/users` · `GET /api/v1/admin/usage/models`
- **Auth:** admin · **Query:** same filters as `/usage/summary`
- **Response 200:** `list[`AdminUserUsageRow`](#adminuserusagerow)` /
  `list[`AdminModelUsageRow`](#adminmodelusagerow)``, biggest consumers first

### `GET /api/v1/admin/usage/timeline`
- **Auth:** admin · **Query:** same filters as `/usage/summary`
- **Response 200:** `list[`UsageTimelinePoint`](#usagetimelinepoint)``, **newest
  first** — one bucket per day (or hour for `range=today`), each with requests,
  failed requests, prompt/completion/total tokens and average latency.

**Analytics filters** (shared by all four endpoints above): `range` is one of
`today` | `7d` | `30d` | `all`; `date_from` / `date_to` are ISO datetimes and
**win over `range`** when both are given; `model` matches the stored model
display name; `user_id` is a UUID. All of them are optional — omitted means
"all time, every model, every user".

These literal paths are registered **before** `GET /admin/usage/{user_id}` so
they can never be swallowed by the path parameter.

### `GET /api/v1/admin/usage/{user_id}`
- **Response 200:** [`UsageOut`](#usageout) · **Errors:** `404 NOT_FOUND`

### `PATCH /api/v1/admin/users/{user_id}/allowance`
- **Request:** `{ "monthly_token_limit": 1000000, "monthly_request_limit": 500, "daily_token_limit": null, "daily_request_limit": null, "is_enabled": true, "reset_at": "2026-10-01T00:00:00Z" }` (all optional)
- **Response 200:** [`UsageOut`](#usageout)
  Fields present in the payload are updated (the service reads
  `model_fields_set`), so sending `daily_token_limit: null` explicitly **clears**
  the daily limit (unlimited) while omitting the key leaves it untouched.
  `is_enabled: false` blocks the user outright, ahead of any token check.

### `POST /api/v1/admin/models` · `PUT /api/v1/admin/models/{model_id}` · `PATCH /api/v1/admin/models/{model_id}/status` · `POST /api/v1/admin/models/{model_id}/default` · `DELETE /api/v1/admin/models/{model_id}`
- **POST/PUT request:** [`ModelCreate`](#modelcreate) / [`ModelUpdate`](#modelcreate)
- **PATCH status request:** `{ "is_active": false }`
- **POST default:** no body — makes exactly one active model the default
  (previous default is cleared); a disabled model cannot become default and
  the default cannot be disabled.
- Enabled Ollama models are verified against the configured Ollama instance
  when reachable (`Model is not available in the configured Ollama instance.`
  otherwise); offline catalog management still works.
- **Response:** `201 ModelOut` / `200 ModelOut` / `200 ModelOut` / `200 ModelOut` / `204`
- **Errors:** `404 NOT_FOUND`, `409 MODEL_NAME_TAKEN`, `422 MODEL_INVALID_CONFIG` / `MODEL_DEFAULT_DISABLE` / `MODEL_NOT_AVAILABLE`

### `POST /api/v1/admin/tools` · `PUT /api/v1/admin/tools/{tool_id}` · `PATCH /api/v1/admin/tools/{tool_id}/status` · `DELETE /api/v1/admin/tools/{tool_id}`
- Same shape as the model endpoints, with `TOOL_NAME_TAKEN` on conflict.

### `GET /api/v1/prompts` · `POST /api/v1/prompts` · `GET /api/v1/prompts/{prompt_id}` · `PATCH /api/v1/prompts/{prompt_id}` · `DELETE /api/v1/prompts/{prompt_id}`
- **Auth:** admin for every method (the list is paginated; `active_only=true`
  narrows it to `status: "active"`).
- **GET response:** paginated [`PromptOut`](#promptout), newest first
- **POST request:** `{ "name": "...", "content": "...", "purpose": "...", "model": null, "version": 1, "status": "draft", "is_default": false }` — only `name` and `content` are required.
- **PATCH request:** any subset of the `PromptOut` fields (`PromptUpdate`).
- **Response:** `201 PromptOut` / `200 PromptOut` / `204`
- **Errors:** `409 PROMPT_NAME_TAKEN`, `404 NOT_FOUND`.
- Setting `is_default: true` clears the previous default in the same
  transaction — at most one prompt is ever the default.

### `GET /api/v1/admin/routing` · `POST /api/v1/admin/routing` · `PUT /api/v1/admin/routing/order` · `PATCH /api/v1/admin/routing/{rule_id}` · `DELETE /api/v1/admin/routing/{rule_id}`
- **Auth:** admin · **GET response:** `list[`RoutingRuleOut`](#routingruleout)`, highest priority first (unpaginated — the rule set is small).
- **POST request:** `{ "request_type": "Code", "primary_model": "llama3.2", "fallback_model": "qwen2.5", "is_active": true }` — `request_type` is unique, `priority` is auto-assigned to the end.
- **PUT order request:** `{ "ids": ["uuid", ...] }` — **every** rule id exactly once, highest priority first.
- **PATCH request:** any subset (`request_type`, `primary_model`, `fallback_model`, `is_active`, `priority`).
- **Response:** `201 RoutingRuleOut` / `list[RoutingRuleOut]` / `200 RoutingRuleOut` / `204`
- **Errors:** `404 NOT_FOUND`, `409 ROUTING_REQUEST_TYPE_TAKEN`, `422` when a
  primary/fallback model is not an active catalog model.

### `GET /api/v1/admin/rate-limits/stats` · `GET /api/v1/admin/rate-limits` · `POST /api/v1/admin/rate-limits` · `PATCH /api/v1/admin/rate-limits/{rule_id}` · `DELETE /api/v1/admin/rate-limits/{rule_id}`
- **Auth:** admin
- **GET stats response:** `{ "date": "2026-09-24", "checked": 8420, "blocked": 120, "violations": 42 }` — today (UTC), best-effort from Redis; zeros when Redis has no data.
- **GET list response:** `list[`RateLimitRuleOut`](#ratelimitruleout)`
- **POST request:** `{ "scope": "all", "limit": 100, "window_seconds": 3600, "action": "block", "is_active": true }` — `limit` and `window_seconds` required, `action` only supports `block`.
- **PATCH request:** any subset.
- **Response:** `200 RateLimitStatsOut` / `200 list` / `201 RateLimitRuleOut` / `200 RateLimitRuleOut` / `204`
- Rules take effect on the **next request** (the rule cache TTL is 30s);
  deleting every rule falls back to the built-in per-minute/per-hour settings.

### `GET /api/v1/admin/audit-logs`
- **Query:** pagination, `action`, `resource_type`, `user_id`
- **Response 200:** paginated [`AuditLogOut`](#auditlogout), newest first

---

## Schemas

### UserOut
```json
{ "id": "uuid", "email": "user@example.com", "name": "User", "role": "user", "is_active": true, "created_at": "...", "updated_at": "..." }
```
`password_hash` is never included in any response.

### ConversationSummary
```json
{ "id": "uuid", "title": "Hello", "created_at": "...", "updated_at": "..." }
```

### MessageOut
```json
{ "id": "uuid", "role": "assistant", "content": "Hello!", "model": "mock", "total_tokens": 12, "created_at": "..." }
```

### ModelOut
```json
{ "id": "uuid", "name": "gpt-4o", "provider": "openai", "model_identifier": "gpt-4o-2024-08-06", "model_type": "chat", "is_active": true, "is_default": false, "max_tokens": 128000, "temperature": 0.7, "created_at": "...", "updated_at": "..." }
```

### ModelCreate
```json
{ "name": "gpt-4o", "provider": "openai", "model_identifier": "gpt-4o-2024-08-06", "model_type": "chat", "is_active": true, "is_default": false, "max_tokens": 128000, "temperature": 0.7 }
```

### ToolOut
```json
{ "id": "uuid", "name": "web-search", "description": "...", "type": "search", "configuration": {}, "is_active": true, "created_at": "...", "updated_at": "..." }
```

### UsageOut
```json
{ "user_id": "uuid", "monthly_token_limit": 10000000, "monthly_request_limit": 1000, "daily_token_limit": null, "daily_request_limit": null, "is_enabled": true, "tokens_used": 21, "requests_used": 2, "tokens_remaining": 9999979, "requests_remaining": 998, "is_allowed": true, "reset_at": "2026-10-01T00:00:00Z" }
```
`daily_*` are `null` = unlimited; `is_enabled: false` blocks the user entirely.

### UsageMeOut
```json
{ "tokens_today": 1200, "requests_today": 3, "tokens_remaining_today": 9900, "requests_remaining_today": 17, "tokens_this_month": 45000, "requests_this_month": 90, "tokens_remaining": 9955000, "requests_remaining": 910, "monthly_token_limit": 10000000, "monthly_request_limit": 1000, "daily_token_limit": null, "daily_request_limit": null, "is_enabled": true, "is_allowed": true, "reset_at": "2026-10-01T00:00:00Z", "current_model": "llama3.2" }
```

### UsageSummaryOut
```json
{ "tokens_today": 1200, "requests_today": 3, "tokens_this_month": 45000, "requests_this_month": 90, "tokens_remaining": 9955000, "current_model": "llama3.2" }
```

### AdminUsageSummary
```json
{ "total_requests": 45230, "successful_requests": 44981, "failed_requests": 249, "cancelled_requests": 180, "total_tokens": 1289340, "prompt_tokens": 890110, "completion_tokens": 399230, "active_users": 87, "average_response_time_ms": 842 }
```

### AdminModelUsageRow
```json
{ "model": "llama3.2", "provider": "ollama", "requests": 820, "successful": 812, "failed": 8, "prompt_tokens": 41000, "completion_tokens": 19000, "total_tokens": 60000, "average_response_time_ms": 742 }
```

### AdminUserUsageRow
```json
{ "user_id": "uuid", "email": "user@example.com", "name": "User", "requests": 120, "successful": 118, "failed": 2, "prompt_tokens": 8000, "completion_tokens": 4000, "total_tokens": 12000, "average_response_time_ms": 810 }
```

### UsageTimelinePoint
```json
{ "period": "2026-09-17", "requests": 42, "failed_requests": 1, "prompt_tokens": 8100, "completion_tokens": 3900, "total_tokens": 12000, "average_response_time_ms": 795 }
```

### PromptOut
```json
{ "id": "uuid", "name": "Default Assistant", "purpose": "General agent behavior", "model": null, "version": 1, "status": "active", "content": "You are a helpful assistant.", "is_default": true, "created_at": "...", "updated_at": "..." }
```
Create requires `name` + `content`; every other field is optional on
`PATCH` (`PromptUpdate`).

### RoutingRuleOut
```json
{ "id": "uuid", "priority": 1, "request_type": "Code", "primary_model": "llama3.2", "fallback_model": "qwen2.5", "is_active": true, "created_at": "...", "updated_at": "..." }
```
Create requires `request_type` + `primary_model` (priority is auto-assigned);
`PUT /admin/routing/order` takes `{ "ids": ["uuid", ...] }` highest priority
first.

### RateLimitRuleOut
```json
{ "id": "uuid", "scope": "all", "limit": 100, "window_seconds": 3600, "action": "block", "is_active": true, "created_at": "...", "updated_at": "..." }
```
`scope` is `all` | `user` | `ip`; create requires `limit` + `window_seconds`.
`GET /admin/rate-limits/stats` returns
`{ "date": "2026-09-24", "checked": 8420, "blocked": 120, "violations": 42 }`.

### DashboardStats
```json
{ "total_users": 120, "active_users": 87, "total_requests": 45230, "total_tokens": 1289340, "active_models": 6, "active_tools": 8 }
```

### AuditLogOut
```json
{ "id": "uuid", "user_id": "uuid", "action": "MODEL_CREATED", "resource_type": "model", "resource_id": "uuid", "ip_address": "127.0.0.1", "user_agent": "...", "metadata": {}, "created_at": "..." }
```

---

## Rate limiting

Enforced per request by the `rate_limit` dependency
(`app/core/rate_limit.py`) using Redis counters. Resolution order:

1. **Active `rate_limit_rules`** from PostgreSQL, cached in Redis under
   `ratelimit:rules:v1` for 30 seconds (DB reads are rare, cache misses cheap).
2. If the rules table is **empty**, the built-in `RATE_LIMIT_PER_MINUTE`
   (default 60) and `RATE_LIMIT_PER_HOUR` (default 1000) settings apply.

Only `action: "block"` exists: exceeding a rule returns
`429 RATE_LIMIT_EXCEEDED`. Counters are keyed per rule + identity (user or
client IP) + window, so they roll over as the window slides. Each request is
also counted in the daily stats hash `ratelimit:stats:{date}` (`checked`,
`blocked`, `violations`), which expires after 7 days — surfaced by
`GET /api/v1/admin/rate-limits/stats`.

Every response includes `X-Response-Time` and `X-Request-ID` headers.

## Prompts

Admin-only CRUD over system prompts. Exactly one prompt may be
`is_default: true` (enforced by a partial unique index); setting a new default
clears the previous one in the same transaction. `status` is `active` |
`draft` | `inactive`, and `GET /prompts?active_only=true` filters to active
prompts — the chat system instruction is taken from the active default.

## Model routing

Admin-only CRUD over `routing_rules`. A rule maps a `request_type` (unique) to
a `primary_model` and optional `fallback_model`; both must be names of active
models in the catalog — the service validates them against the same allow-list
chat uses, so routing can never select a disabled model. `priority` is
dense and ascending (1 = first); `PUT /admin/routing/order` takes the full id
list highest-priority first, and `DELETE` renumbers the rest.

ChatService consults routing **only** when the request supplies a
`request_type` **and** no explicit `model`; an explicit `model` always wins.

## Audit actions

`USER_LOGIN`, `USER_LOGOUT`, `USER_CREATED`, `USER_UPDATED`, `USER_DELETED`,
`MODEL_CREATED`, `MODEL_UPDATED`, `MODEL_DISABLED`, `TOOL_CREATED`,
`TOOL_UPDATED`, `TOOL_DISABLED`, `USAGE_LIMIT_UPDATED`, `API_KEY_CREATED`,
`API_KEY_REVOKED`.

## Roadmap (intentionally out of scope)

The agent engine, RAG pipeline and tool execution remain placeholders
(`app/agents/`) so they can be integrated without changing the API or service
layers. Real-time streaming (`POST /api/v1/chat/stream`) and the
backend-controlled Ollama model platform are now implemented.
