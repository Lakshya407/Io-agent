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
{ "message": "Hello", "conversation_id": null, "model": null }
```
  Omit `conversation_id` to start a new conversation; pass an existing one to
  continue it. `model` overrides the default model; it must be an active model
  in the catalog (or the configured default), otherwise `422
  MODEL_NOT_AVAILABLE` is returned — the frontend cannot run arbitrary models.
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
- **Auth:** user · **Query:** pagination, `active_only=true`
- **Response 200:** paginated [`ModelOut`](#modelout)

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

### `GET /api/v1/usage` — my allowance
- **Auth:** user
- **Response 200:** [`UsageOut`](#usageout)

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

### `GET /api/v1/admin/usage/{user_id}`
- **Response 200:** [`UsageOut`](#usageout) · **Errors:** `404 NOT_FOUND`

### `PATCH /api/v1/admin/users/{user_id}/allowance`
- **Request:** `{ "monthly_token_limit": 1000000, "monthly_request_limit": 500, "reset_at": "2026-10-01T00:00:00Z" }` (all optional)
- **Response 200:** [`UsageOut`](#usageout)

### `POST /api/v1/admin/models` · `PUT /api/v1/admin/models/{model_id}` · `PATCH /api/v1/admin/models/{model_id}/status` · `DELETE /api/v1/admin/models/{model_id}`
- **POST/PUT request:** [`ModelCreate`](#modelcreate) / [`ModelUpdate`](#modelcreate)
- **PATCH status request:** `{ "is_active": false }`
- **Response:** `201 ModelOut` / `200 ModelOut` / `200 ModelOut` / `204`
- **Errors:** `404 NOT_FOUND`, `409 MODEL_NAME_TAKEN`

### `POST /api/v1/admin/tools` · `PUT /api/v1/admin/tools/{tool_id}` · `PATCH /api/v1/admin/tools/{tool_id}/status` · `DELETE /api/v1/admin/tools/{tool_id}`
- Same shape as the model endpoints, with `TOOL_NAME_TAKEN` on conflict.

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
{ "user_id": "uuid", "monthly_token_limit": 10000000, "monthly_request_limit": 1000, "tokens_used": 21, "requests_used": 2, "tokens_remaining": 9999979, "requests_remaining": 998, "is_allowed": true, "reset_at": "2026-10-01T00:00:00Z" }
```

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

Applied per user (or per client IP for unauthenticated endpoints) via Redis:
`RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_PER_HOUR` requests. Exceeding the limit
returns `429 RATE_LIMIT_EXCEEDED`. Every response includes `X-Response-Time`
and `X-Request-ID` headers.

## Audit actions

`USER_LOGIN`, `USER_LOGOUT`, `USER_CREATED`, `USER_UPDATED`, `USER_DELETED`,
`MODEL_CREATED`, `MODEL_UPDATED`, `MODEL_DISABLED`, `TOOL_CREATED`,
`TOOL_UPDATED`, `TOOL_DISABLED`, `USAGE_LIMIT_UPDATED`, `API_KEY_CREATED`,
`API_KEY_REVOKED`.

## Roadmap (intentionally out of scope)

Streaming responses, the agent engine, RAG pipeline and tool execution remain
placeholders (`app/agents/`) so they can be integrated without changing the API
or service layers.
