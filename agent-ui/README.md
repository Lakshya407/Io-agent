# AI Agent Platform — Frontend

React + Vite + TypeScript UI for the AI Agent Platform, connected to the
FastAPI backend. The interface consumes the real API (JWT auth, PostgreSQL
data, Redis-backed rate limiting) — no hardcoded or mock data remains for any
backend-managed feature.

## Project Overview

- **AI Agent Platform frontend** — chat workspace + admin console
- **React 18** with **Vite** and **TypeScript** (strict)
- **Tailwind-free** hand-written CSS (existing design preserved verbatim)
- **TanStack Query** for server-state: caching, dedup, loading/error/empty
  states and cache invalidation
- **FastAPI backend** as the single source of truth (PostgreSQL + Redis)

## Architecture

```
Browser
   │
   ▼
React components (pages/)
   │
   ▼
Hooks (hooks/use*)          ← loading / error / empty states, mutations
   │
   ▼
API functions (api/*)       ← typed requests + response adapters
   │
   ▼
API client (api/client.ts)  ← base URL, JWT, timeout, refresh, retry
   │
   ▼
FastAPI (/api/v1)           ← PostgreSQL + Redis
```

Every request flows through one client, so auth headers, timeouts, request
ids and error handling are defined exactly once.

## Folder Structure

```
agent-ui/
├── src/
│   ├── api/            # client.ts + one module per backend resource
│   │   ├── client.ts   # centralized fetch client (auth, timeout, refresh)
│   │   ├── auth.ts
│   │   ├── users.ts
│   │   ├── chat.ts     # chat + conversations
│   │   ├── models.ts
│   │   ├── tools.ts
│   │   ├── usage.ts
│   │   ├── admin.ts
│   │   ├── prompts.ts    # system prompt CRUD (admin)
│   │   ├── routing.ts    # model routing rules (admin)
│   │   ├── rateLimits.ts # rate limit rules + daily stats (admin)
│   │   ├── auditLogs.ts
│   │   └── health.ts
│   ├── hooks/          # TanStack Query wrappers per resource
│   ├── types/          # TypeScript types mirroring the Pydantic schemas
│   ├── context/        # AuthContext (session) + ToastContext (feedback)
│   ├── components/
│   │   ├── admin/      # tables, modals, filters, stat cards, pagination
│   │   ├── chat/       # chat window, history sidebar, message input, usage
│   │   └── agent/      # activity panel, tool calls, status
│   ├── pages/
│   │   ├── Chat.tsx
│   │   ├── Login.tsx       # the single sign-in page (user + admin)
│   │   ├── Register.tsx    # user sign-up
│   │   ├── Unauthorized.tsx # 403 page (authenticated, not permitted)
│   │   └── admin/      # overview, users, usage, models, tools, prompts, …
│   ├── auth/            # route guards + post-login routing
│   │   ├── ProtectedRoute.tsx  # requires a valid session (any user)
│   │   ├── RoleRoute.tsx       # additionally requires a backend role
│   │   ├── RootRedirect.tsx    # "/" → /login | /admin | /chat by role
│   │   └── ForbiddenRedirect.tsx # reacts to API 403s
│   ├── utils/          # formatting helpers + response adapters
│   └── lib/            # queryClient + query-key factory
├── nginx.conf          # SPA fallback + reverse proxy to the backend
├── Dockerfile          # multi-stage Node → Nginx production image
├── .env.example        # documented environment template
└── package.json
```

## Requirements

- **Node.js 22+** (LTS) and **npm**
- A running backend at `http://localhost:8000` (see `../backend`)
- **Docker** + **Docker Compose** for the containerized stack

## Local Development

```bash
npm install
npm run dev
```

The dev server starts on **http://localhost:5173**.

### Environment

Copy the template and adjust if your backend runs elsewhere:

```bash
cp .env.example .env
```

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Only variables prefixed with `VITE_` reach the browser. Never put secrets
(database passwords, JWT secret, provider keys) in a frontend `.env` — the
browser can read anything prefixed with `VITE_`.

## Backend Requirement

The backend must be running before the frontend can show real data:

- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health` and `/health/ready`

Start it from `../backend`:

```bash
cd ../backend
docker compose up --build        # or: uvicorn app.main:app --reload
```

The default administrator is seeded on first startup from
`DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD` in `backend/.env`
(`admin@example.com` / `change-me-now` by default).

## Environment Variables

| Variable | Development | Production | Purpose |
|---|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | `/api/v1` | Backend base URL |

Production uses a **relative** path because Nginx reverse-proxies `/api` to
the backend container, so the browser and the API share one origin and no
CORS preflight happens.

## Docker

The full stack (frontend + backend + PostgreSQL + Redis) is orchestrated by
the root `docker-compose.yml`:

```bash
cd ..
docker compose up --build
```

- Frontend (Nginx): **http://localhost**
- Backend API: `http://localhost/api/v1` (through the proxy)
- Swagger docs: `http://localhost/docs` (through the proxy)

Stop the stack:

```bash
docker compose down
```

PostgreSQL and Redis are only reachable inside the private `ai-agent-network`
— they are never published to the host.

## API Architecture

```
Component ──► Hook ──► API function ──► API client ──► FastAPI
   ▲                                           │
   └─────────── cache invalidation ────────────┘
```

- **API client** (`src/api/client.ts`) — base URL from `VITE_API_BASE_URL`,
  `Authorization: Bearer` injection, `X-Request-ID` propagation, per-request
  timeout, single-flight token refresh with transparent retry, one bounded
  retry for idempotent GETs, and normalization of the backend error envelope
  into an `APIError`.
- **Hooks** — TanStack Query wrappers exposing `data` / `isLoading` / `error`
  / `refetch`, plus mutations that invalidate the right query keys.
- **Adapters** (`src/utils/adapters.ts`) — map backend field names onto the
  shapes the existing components expect, so no component had to be rewritten.

### Backend Endpoints

| Module | Endpoint |
|---|---|
| Auth | `/api/v1/auth/login`, `/auth/refresh`, `/auth/me`, `/auth/register` |
| Users | `/api/v1/users`, `/users/me`, `/users/{id}` |
| Chat | `POST /api/v1/chat` |
| Conversations | `/api/v1/conversations`, `…/messages`, `DELETE …/{id}` |
| Models | `/api/v1/models`, `/admin/models` (POST/PUT/PATCH/DELETE) |
| Tools | `/api/v1/tools`, `/admin/tools` (POST/PUT/PATCH/DELETE) |
| Usage | `/api/v1/usage`, `/usage/me`, `/usage/summary`, `/usage/history` |
| Usage analytics | `/admin/usage/summary`, `/admin/usage/users`, `/admin/usage/models`, `/admin/usage/timeline` (range/model/user filters) |
| Admin | `/api/v1/admin/dashboard`, `/admin/audit-logs`, `/admin/users/{id}/allowance` |
| Prompts | `/api/v1/prompts` + `/{id}` (GET/POST/PATCH/DELETE, admin) |
| Routing | `/admin/routing`, `/admin/routing/order`, `/admin/routing/{id}` |
| Rate limits | `/admin/rate-limits`, `/admin/rate-limits/stats`, `/admin/rate-limits/{id}` |

### Usage

Usage is server-owned end to end:

- **Chat sidebar** — `UsageIndicator` sits above the user menu and shows
  today's and this month's tokens/requests, the remaining monthly allowance and
  the model the next message will use. It renders nothing while loading or if
  the endpoint errors, so usage trouble never disturbs the chat UI.
- **Cache invalidation** — every completed, failed or stopped turn invalidates
  the `["usage"]` prefix, so the indicator and allowance refresh themselves.
- **Admin analytics** (`Usage`, `API Usage`, `User Analytics`) share one filter
  shape — range (`today` / `7d` / `30d` / custom), model and user — sent to the
  four `/admin/usage/*` endpoints. Explicit custom dates win over the range.

## Authentication Architecture

The application is structured around **authentication first, then role-based
access control**. Nothing protected renders before the session is resolved,
and the FastAPI backend is always the real authority on *who the user is* and
*what they may do*.

```
Browser
   ↓
Authentication (AuthContext ↔ POST /auth/login, GET /auth/me)
   ↓
Role Detection (from GET /auth/me — never local storage)
   ├── user  → Chat (/chat)
   └── admin → Admin Dashboard (/admin) + Chat (/chat)
```

### User

```text
/login → /chat
```

### Admin

```text
/login → /admin → (all admin modules) + /chat
```

### Authorization

```text
Frontend route guards  → navigation / UX protection
        +
Backend RBAC (FastAPI) → actual security enforcement
```

Frontend guards (`ProtectedRoute`, `RoleRoute`) keep navigation consistent;
FastAPI re-validates authentication **and** the role on every request. A
normal user calling an admin endpoint receives `403 Forbidden` regardless of
any client-side state, so editing `localStorage`, frontend state or the URL
cannot elevate access.

### Route structure

```text
/                     → RootRedirect: loading → /login → /admin | /chat
/login, /register     → public
/unauthorized         → authenticated but not permitted (403)

ProtectedRoute        → valid session required
   /chat
   RoleRoute(admin)   → real backend role "admin" required
      /admin, /admin/users, /admin/models, /admin/tools,
      /admin/prompts, /admin/routing, /admin/analytics,
      /admin/audit-logs, /admin/rate-limits, …
```

### Details

- **Login** — `/login` posts to `POST /auth/login` (OAuth2 form:
  `username` = email), then loads the user via `GET /auth/me`. There is
  **one** authentication flow for users and admins — no separate admin
  sign-in. After login the route is chosen from the real role: `admin` →
  `/admin`, `user` → `/chat`. A requested destination (captured in
  `?redirect=` by `ProtectedRoute`) is honoured only when that role may
  reach it, so a normal user is never sent into `/admin`.
- **Register** — `/register` calls `POST /auth/register` and authenticates
  immediately (the backend issues tokens on success). New accounts are
  normal users; only an admin can promote a role.
- **No UI flash** — while the session is being restored/validated the guards
  render only a minimal "Checking authentication…" screen. Neither the Chat
  UI nor the Admin UI can appear before authentication is resolved.
- **Token storage** — the short-lived **access token is kept in memory only**;
  the longer-lived **refresh token** is persisted so a page refresh silently
  restores the session. The user object and role are **never** persisted —
  they are re-read from `GET /auth/me` on every start.
- **Remember me** — controls whether the refresh token is persisted, so an
  unchecked box genuinely ends the session on browser restart.
- **401 handling** — on a `401` the client performs a single refresh and
  retries the original request once. If the refresh fails the session is
  cleared and the user is redirected to `/login?redirect=<current path>`.
- **403 handling** — a `403` is never converted to a `401`: the session stays
  intact (a valid user can simply be unauthorized for a resource). The UI is
  notified and sends the user to `/unauthorized`; pages that prefer an inline
  message can render the `APIError` instead.
- **Roles** — `admin` / `user` come from `GET /auth/me` only. Admin pages are
  guarded client-side for UX; the backend enforces authorization on every
  `/admin/*` request (`403 FORBIDDEN` otherwise). No role is ever
  hard-coded or read from local storage.
- **Admin chat** — admins open `/chat` from the admin sidebar using the same
  session. There is exactly one authentication; no second sign-in.
- **Logout** — the sidebar user menu clears all stored credentials and the
  query cache; the route guard then redirects to `/login`.
- **Not yet implemented by the backend** — password reset and SSO/Azure AD
  have no corresponding endpoint. "Forgot password?" surfaces an honest
  notice instead of a fake email flow, and the SSO button is visibly
  disabled as "coming soon".

## State Handling

- **Loading** — each API-driven section renders a spinner (`LoadingState`)
  instead of an empty or broken layout.
- **Errors** — normalized `APIError` → a friendly message with a "Try again"
  button (`ErrorState`). Raw stack traces are never shown.
- **Empty** — tables show a contextual empty message when the backend returns
  no rows.
- **Mutations** — succeed-then-refresh (no optimistic UI for administrative
  operations), with a toast confirming the result.
- **Pagination** — collection pages walk `?page=N&page_size=M` server-side;
  no large result set is paginated in the browser.

## Demo Pages

Two admin pages — **Knowledge Base** and **Agent Activity** — cover features
the backend does not implement yet: there are no endpoints for them, so none
were invented. They retain clearly-labelled static demo data
(`src/data/knowledgeBase.ts`, `src/data/activity.ts`) and are out of scope for
this integration.

Every other admin page (Overview, Users, Usage, Models, Tools, Audit Logs,
**Prompts**, **Model Routing**, **Rate Limits**, **API Usage**,
**User Analytics**) is driven by the real API through TanStack Query, with
loading, error, empty and pagination states.

## Troubleshooting

- **`CORS error` in the browser console** — the backend `CORS_ORIGINS` must
  include the dev origin (`http://localhost:5173`). In production the Nginx
  proxy removes cross-origin requests entirely.
- **`Unable to reach the server`** — the backend is down or
  `VITE_API_BASE_URL` points at the wrong host. Check `http://localhost:8000/health`.
- **`401 Unauthorized`** — session expired and the refresh token is invalid;
  sign in again. If it happens immediately, the credentials are wrong.
- **`403 Forbidden` on admin pages** — the signed-in user's role is not
  `admin`. The backend is authoritative; the UI only hides the pages.
- **`404` after a hard refresh of `/admin/users`** — only when served without
  the SPA fallback; the bundled Nginx config handles this via
  `try_files $uri $uri/ /index.html`.
- **Docker: browser cannot resolve `backend`** — never set
  `VITE_API_BASE_URL=http://backend:8000`. That hostname is container-internal
  and unreachable from the browser. Use the relative `/api/v1` path served by
  the Nginx proxy.
- **Environment variable not applied** — Vite only exposes `VITE_`-prefixed
  variables at build time; restart `npm run dev` (or rebuild the image) after
  editing `.env`.
