# Io-agent

Self-hosted AI chat platform for internal use. Open WebUI provides the chat UI and
Microsoft Entra ID single sign-on; LiteLLM exposes one OpenAI-compatible model
catalog; OmniRoute routes free/cloud providers; Ollama serves local models.

- **Host:** `io-op-k8s` (`172.30.30.154`)
- **Public URL:** https://ioagentics.infoorigin.com
- **Deployment:** Docker Compose in `~/Io-agent/litellm`

## Architecture

```text
Browser
  |  HTTPS 443
  v
Nginx (host)
  |  reverse proxy -> 127.0.0.1:8080
  v
Open WebUI
  |  OpenAI-compatible /v1
  v
LiteLLM (:4000)
  |---> Ollama (host.docker.internal:11434)  -> local models
  |---> OmniRoute (:20128)                   -> DuckDuckGo / OpenRouter
  `---> OpenAI API                           -> gpt-5-nano (direct)
```

PostgreSQL stores LiteLLM keys, spend logs and configuration state. Open WebUI,
OmniRoute and LiteLLM each keep their own Docker volume.

## Components

| Component | Role | Listener |
|---|---|---|
| Open WebUI | Chat UI, users, chat history, Entra ID SSO | `127.0.0.1:8080` |
| LiteLLM | Model gateway, auth, model catalog, spend logs | `0.0.0.0:4000` |
| OmniRoute | Provider routing, cooldowns, dashboard | `127.0.0.1:20128` |
| Ollama | Local inference runtime | `0.0.0.0:11434` |
| PostgreSQL 16 | LiteLLM database | `0.0.0.0:5432` |
| Nginx | TLS termination and public entry point | `80`, `443` |
| Microsoft Entra ID | OIDC identity provider | External |

## Repository layout

```text
Io-agent/
`-- litellm/
    |-- docker-compose.yml    # postgres, omniroute, litellm, open-webui
    |-- config.yml            # LiteLLM model catalog
    |-- .env                  # LiteLLM, Open WebUI, SSO and provider secrets
    `-- omniroute.env         # OmniRoute runtime secrets
```

`.env` and `omniroute.env` contain secrets and must never be committed.

## Prerequisites

- Docker Engine with Compose v2
- Ollama installed and running on the host
- A Microsoft Entra ID app registration for Open WebUI
- At least one model pulled into Ollama:

```bash
ollama pull qwen2.5:0.5b
ollama list
```

## Configuration

Create `litellm/.env` (do not commit it):

```dotenv
# LiteLLM / OpenAI
OPENAI_API_KEY=
LITELLM_MASTER_KEY=sk-
POSTGRES_PASSWORD=
DATABASE_URL=postgresql://litellm:<password>@postgres:5432/litellm
OMNIROUTE_API_KEY=

# Open WebUI
WEBUI_NAME=Io-agent
WEBUI_URL=https://ioagentics.infoorigin.com
WEBUI_SECRET_KEY=
ENABLE_OAUTH=true
ENABLE_OAUTH_SIGNUP=true
DEFAULT_USER_ROLE=user
OAUTH_MERGE_ACCOUNTS_BY_EMAIL=false
BYPASS_MODEL_ACCESS_CONTROL=true
FORWARDED_ALLOW_IPS=*

# Microsoft Entra ID
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
MICROSOFT_CLIENT_TENANT_ID=
MICROSOFT_OAUTH_SCOPE=openid email profile offline_access
MICROSOFT_REDIRECT_URI=https://ioagentics.infoorigin.com/oauth/microsoft/callback
OPENID_PROVIDER_URL=https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration
```

`DATABASE_URL` must use the same password as `POSTGRES_PASSWORD`.

Create `litellm/omniroute.env`:

```dotenv
NODE_ENV=production
PORT=20128
HOSTNAME=0.0.0.0
DATA_DIR=/app/data
JWT_SECRET=
API_KEY_SECRET=
STORAGE_ENCRYPTION_KEY=
REQUIRE_API_KEY=true
INITIAL_PASSWORD=
OMNIROUTE_WS_BRIDGE_SECRET=
```

Generate long random values for all secrets. Change the OmniRoute bootstrap
password before exposing the service.

### Microsoft Entra ID

1. Create a single-tenant app registration.
2. Add the Web redirect URI:
   `https://ioagentics.infoorigin.com/oauth/microsoft/callback`
3. Create a client secret and copy the application, tenant and secret values
   into `.env`.
4. Grant the delegated permissions `openid`, `email`, `profile` and
   `offline_access`; grant admin consent.
5. Assign the users or groups that should have access.

Open WebUI uses its native Microsoft OAuth flow. No separate LiteLLM SSO
configuration is required for this deployment.

## Start and stop

```bash
cd ~/Io-agent/litellm
docker compose up -d
docker compose ps
```

```bash
docker compose stop
docker compose down          # keeps named volumes
docker compose down -v       # DESTROYS data; do not use casually
```

`config.yml` is mounted read-only. Restart LiteLLM after editing it:

```bash
docker compose restart litellm
```

Environment changes for Open WebUI require recreating the container:

```bash
docker compose up -d --force-recreate open-webui
```

## Model catalog

Model names in `config.yml` are what users see in Open WebUI. The target
(`litellm_params.model`) determines where the request actually goes.

| Model path | Backend | Notes |
|---|---|---|
| `qwen2.5-0.5b` | Ollama | Local inference; data stays on the VM |
| `free-gpt-5.4-mini`, `free-claude-haiku-4-5` | OmniRoute -> DuckDuckGo AI Chat | Keyless, unofficial, no SLA |
| `openrouter-*` | OmniRoute -> OpenRouter | Free-tier models; upstream limits apply |
| `gpt-5-nano` | OpenAI API, direct | Bypasses OmniRoute; paid fallback |

The authoritative list is always `litellm/config.yml`.

To add a model:

1. Add or activate the provider in the OmniRoute dashboard.
2. Test the exact upstream model ID with a direct OmniRoute request.
3. Add an entry under `model_list` in `config.yml`.
4. Restart LiteLLM and verify `GET /v1/models`.
5. Refresh Open WebUI; the model appears in the picker.

OmniRoute model IDs use the form `<provider-alias>/<upstream-model-id>`. LiteLLM
entries that route through OmniRoute use `model: openai/<omniroute-model-id>` and
`api_base: http://omniroute:20128/v1`.

## Verification

```bash
# Ollama
curl -s http://127.0.0.1:11434/api/tags

# LiteLLM catalog
curl -s http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"

# LiteLLM chat completion
curl -s http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-0.5b","messages":[{"role":"user","content":"ping"}],"stream":false}'
```

Substitute the value from `.env` if `$LITELLM_MASTER_KEY` is not exported in your
shell. Use the OmniRoute dashboard (via the SSH tunnel below) to check provider
health.

Open WebUI: https://ioagentics.infoorigin.com

## Operations

```bash
cd ~/Io-agent/litellm

# Status
docker compose ps

# Logs
docker compose logs -f --tail=100 litellm
docker compose logs -f --tail=100 open-webui
docker compose logs -f --tail=100 omniroute

# Restart one service
docker compose restart litellm

# Pull newer images and recreate
docker compose pull
docker compose up -d
```

Back up configuration and data before upgrades:

```bash
cp config.yml "config.yml.bak.$(date +%Y%m%d-%H%M%S)"
docker run --rm -v litellm_postgres_data:/data -v "$PWD":/backup alpine \
  tar czf /backup/postgres_data.tgz -C /data .
```

If the actual volume name differs, confirm it with `docker volume ls`.

### OmniRoute dashboard

The dashboard is bound to loopback only. Open an SSH tunnel from your workstation:

```bash
ssh -L 20128:127.0.0.1:20128 -i k8s.pem ubuntu@172.30.30.154
```

Then browse http://localhost:20128/dashboard. Closing the tunnel affects only
dashboard access; model traffic does not use it.

## Security notes

- `.env` contains the LiteLLM master key, OpenAI key, database password,
  OmniRoute key and Entra ID secret. Restrict it to the deployment user:
  `chmod 600 .env`.
- LiteLLM (`4000`) and PostgreSQL (`5432`) currently listen on all interfaces.
  Bind them to `127.0.0.1` or restrict them with a host firewall before wider use.
- `BYPASS_MODEL_ACCESS_CONTROL=true` lets every signed-in user select every
  model, including paid models. Replace it with per-model access control when the
  user base grows.
- `ENABLE_OAUTH_SIGNUP=true` allows accounts to be created automatically. Limit
  access through the Entra ID enterprise application assignment.
- Cloud models send prompts, attachments and responses outside the org.
  DuckDuckGo AI Chat and OpenRouter free tiers are best-effort and have no
  enterprise data-processing guarantee. Use Ollama models for confidential data.
- OmniRoute detailed call logging and LiteLLM spend logs can store full request
  and response bodies. Disable body logging, reduce retention and purge existing
  logs if prompts must not be retained at rest.
- Change the OmniRoute `INITIAL_PASSWORD` before exposing the dashboard.
- Image tags are floating (`main-latest`, `latest`). Pin versions for reproducible
  deployments.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Normal users see no models | Model access control | Set `BYPASS_MODEL_ACCESS_CONTROL=true`, recreate Open WebUI, or grant per-model access |
| `401` from LiteLLM | Missing/wrong master key | Check `LITELLM_MASTER_KEY` and the client `Authorization` header |
| `429 All credentials cooling down` | Upstream provider rate limit | Wait for the cooldown, reduce concurrency, or add another provider/account |
| `404 Provider returned error` | Wrong upstream model ID | Refresh the provider catalog and use the exact model ID |
| New `config.yml` ignored | LiteLLM not restarted | `docker compose restart litellm` |
| Open WebUI env change ignored | Container not recreated | `docker compose up -d --force-recreate open-webui` |
| SSO redirect error | Redirect URI mismatch | Match the Entra ID Web redirect URI exactly |
| OmniRoute dashboard unreachable | SSH tunnel closed | Reopen the `-L 20128:...` tunnel |
| `permission denied` on Docker | User not in `docker` group | Use `sudo docker ...` or grant Docker access |
