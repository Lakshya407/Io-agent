# Io-agent — OpenWebUI + LiteLLM + Ollama

Local AI stack: `Io-agent` (OpenWebUI v0.6.5) for chat, `LiteLLM` proxy for OpenAI-compatible gateway, `Ollama` for local models, `Postgres` for LiteLLM storage.

```
User -> http://localhost:3000 (io-agent/open-webui)
         ├──> http://ollama:11434 (local: deepseek-r1:1.5b, qwen2.5-coder:3b)
         └──> http://litellm:4000 (gateway: gpt-5-nano via OpenAI)
                └──> postgres:5432 (litellm DB)
```

## Repos / Folders

- `open-webui/` — UI + Ollama, `docker-compose.yaml` + `.env` (not committed)
- `litellm/` — gateway, `docker-compose.yml` + `config.yml`

## Prerequisites

- Docker Desktop (WSL2), Git
- Ports free: `3000`, `4000`, `5432`
- Azure App Registration (for SSO), OpenAI API key (for LiteLLM)

## Quick Setup

1. Clone/copy this folder so `litellm/` and `open-webui/` sit side by side.

2. Configure `open-webui/.env` (create from below, never commit secrets):
```env
OLLAMA_BASE_URL=http://ollama:11434
WEBUI_URL=http://localhost:3000
WEBUI_NAME=Io-agent
WEBUI_SECRET_KEY=
ENABLE_OAUTH_SIGNUP=true
OAUTH_MERGE_ACCOUNTS_BY_EMAIL=true
MICROSOFT_CLIENT_ID=<azure-app-id>
MICROSOFT_CLIENT_SECRET=<azure-secret>
MICROSOFT_CLIENT_TENANT_ID=<azure-tenant-id>
MICROSOFT_OAUTH_SCOPE=openid email profile offline_access
MICROSOFT_REDIRECT_URI=http://localhost:3000/oauth/microsoft/callback
OPENID_PROVIDER_URL=https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration
DEFAULT_USER_ROLE=user
BYPASS_MODEL_ACCESS_CONTROL=true
OPEN_WEBUI_PORT=3000
```

3. Configure `litellm/docker-compose.yml` env: `OPENAI_API_KEY`, `LITELLM_MASTER_KEY`, `DATABASE_URL`. Models in `litellm/config.yml`.

4. Start:
```powershell
cd litellm; docker compose up -d
cd ../open-webui; docker compose up -d
docker network connect open-webui_default litellm
```

5. Verify:
- UI: `http://localhost:3000/api/config` → `name=Io-agent`
- Gateway: `GET http://localhost:4000/models` with `Authorization: Bearer <LITELLM_MASTER_KEY>` → `gpt-5-nano`
- Chat: login → `Select a model` lists local + gateway models.

## OpenWebUI ↔ LiteLLM Connection

Admin UI → Connections, or `config.openai` in DB:
- URL: `http://litellm:4000` (container-to-container, requires step 4 network connect)
- Key: `<LITELLM_MASTER_KEY>` (default `sk-master-12345`)
- Outside Docker use `http://host.docker.internal:4000`. Re-run `network connect` after any `compose up -d` recreate if models disappear.

## Azure AD SSO

App registrations → New → Single tenant → Redirect URI `Web`:
- OpenWebUI: `http://localhost:3000/oauth/microsoft/callback`
- LiteLLM UI: `http://localhost:4000/sso/callback`

Then: copy Application/Tenant ID, create client secret, API permissions `openid email profile User.Read offline_access` → Grant admin consent, Token config optional claim `email`, assign Users/groups.

OpenWebUI uses `MICROSOFT_*` native flow (`Continue with Microsoft`). LiteLLM uses `MICROSOFT_CLIENT_ID/SECRET/TENANT` + `PROXY_BASE_URL=http://localhost:4000`.

## Roles / Model Access

- New SSO users get `DEFAULT_USER_ROLE=user` (was `pending` → no chat). Promote in Admin → Users.
- Direct gateway models need `BYPASS_MODEL_ACCESS_CONTROL=true`, else users see `No results found` / `403 Model not found` (`routers/openai.py:525`).
- Normal-user `POST /users/update/role 403` is expected (admin only).
- Signout needs `OPENID_PROVIDER_URL` set, else `GET /auths/signout 500`.

## On-prem / New Device

Same as Quick Setup + update `WEBUI_URL` / `MICROSOFT_REDIRECT_URI` to new host and add that URI in Azure. Either move Ollama to server (`ollama pull ...`) or expose PC Ollama via Tailscale and set `OLLAMA_BASE_URL=http://<pc-ip>:11434`.

## Troubleshooting

- `services.image must be a mapping` → fix compose indentation.
- `/models` empty → `docker network inspect open-webui_default` must list `litellm`; if not, reconnect.
- `Need admin approval` → Grant admin consent in Azure + assign user to Enterprise App.
- LiteLLM SSO needs Enterprise license (free ≤5 users).
