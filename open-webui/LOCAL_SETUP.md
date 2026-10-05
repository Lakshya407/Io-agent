# LOCAL_SETUP.md — Io-agent v0.6.5 Local Development Environment

> **Branded build.** This tree is rebranded to **Io-agent**. See
> `REBRAND.md` for the full change log and `DEPLOYMENT.md` for taking it
> to your on-prem server.

> Baseline setup only. **No branding or functionality changes have been made.**
> Companion documents: `BASELINE.md` (recorded baseline) and `BRANDING_AUDIT.md`
> (branding inventory for the next phase).

---

## 1. Prerequisites

| Requirement | Minimum | Version used on this machine |
| ----------- | ------- | ---------------------------- |
| OS | Windows 10/11, Linux, or macOS | Windows 11 Pro (10.0.26200), 64-bit |
| CPU | 2+ cores | 11th Gen Intel i5-11320H, 4 cores / 8 threads |
| RAM | 8 GB (16 GB recommended) | 15.8 GB total |
| Disk | ~15 GB free for images + build cache | D: ≈ 985 GB free, C: ≈ 74 GB free |
| Docker | 20.10+ | Docker 29.8.1 |
| Docker Compose | v2.x (`docker compose`) | Docker Compose v5.5.1 |
| Git | 2.30+ | 2.55.0.windows.5 |
| Node.js | 18.13 – 22.x (`package.json` engines) | v22.23.3 (inside Docker: node:22-alpine3.20) |
| npm | 6.0+ | 10.9.9 |
| Python | 3.11 – 3.12 (`pyproject.toml`) | 3.14.6 on host (unused; backend runs in container with Python 3.11) |

> **Note:** Host Python 3.14 is **outside** the supported range (`>=3.11,<3.13`).
> This is why the Docker path is used: the container ships Python 3.11 and the
> correct dependency set. No host Python dependencies are required.

No local Node/Python build toolchain is needed — both frontend and backend are
built inside Docker.

---

## 2. Repository version

| Field | Value |
| ----- | ----- |
| Upstream | https://github.com/open-webui/open-webui |
| Tag | **`v0.6.5`** |
| Commit | `07d8460126a686de9a99e2662d06106e22c3f6b6` |
| Clone location | `D:\open-webui` |

Verification:

```bash
git describe --tags --always   # v0.6.5
git log -1 --oneline           # 07d84601 Merge pull request #12809 from open-webui/dev
```

---

## 3. Git branch

```bash
git branch                     # custom-branding-v0.6.5
git status                     # On branch custom-branding-v0.6.5
```

`custom-branding-v0.6.5` is created **directly on top of the `v0.6.5` tag**. It is
the clean baseline from which all future customization will branch.

### The single tracked change: `Dockerfile` (build memory)

Exactly **one** tracked file is modified versus `v0.6.5`:

```bash
git diff --stat HEAD
#  Dockerfile | 10 ++++++++++
#  1 file changed, 10 insertions(+)
```

| Item | Value |
| ---- | ----- |
| File | `Dockerfile`, frontend `build` stage (upstream line 34, `RUN npm run build`) |
| Change | Added `ENV NODE_OPTIONS=--max-old-space-size=4096` + explanatory comment |
| Why | Docker Desktop VM = 7.65 GB ⇒ Node's default V8 heap cap in the build = 2096 MB. `vite build` exceeds it → `FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory` |
| Scope | `build` stage only. The runtime stage is a separate `FROM` and does **not** inherit this `ENV` |
| Impact on app | **None.** No dependency version, source file, config value, or UI string changed |
| Revert | `git checkout -- Dockerfile` (then the build will OOM again on this machine) |

Everything else (frontend `src/`, `static/`, `backend/`, `package.json`,
`requirements.txt`) is byte-identical to upstream `v0.6.5`.

---

## 4. Directory structure

```
D:\open-webui\
├── src/                        # SvelteKit frontend source
│   ├── app.html                # HTML shell: <title>, meta, splash screen
│   ├── routes/                 # Pages (auth/, (app)/, +layout.svelte)
│   └── lib/
│       ├── components/         # UI components (chat, admin, layout, workspace)
│       ├── apis/               # Frontend -> backend API clients
│       ├── stores/             # Svelte stores (WEBUI_NAME, user, config)
│       ├── i18n/locales/       # 54 translation locales
│       └── constants.ts        # APP_NAME, WEBUI_VERSION
├── static/                     # Frontend static assets (copied into build)
│   ├── static/                 # favicon*, splash*, site.webmanifest, PWA icons
│   ├── assets/                 # fonts, images, emojis
│   ├── themes/                 # CSS themes
│   ├── manifest.json           # (empty object)
│   └── opensearch.xml          # Browser search branding
├── backend/
│   ├── start.sh                # Container entrypoint (uvicorn)
│   ├── requirements.txt        # Pinned Python deps (used by Docker build)
│   └── open_webui/
│       ├── main.py             # FastAPI app + routers + static mounts
│       ├── env.py              # Environment/config (WEBUI_NAME, DATABASE_URL)
│       ├── config.py           # App config + Alembic migration runner
│       ├── routers/            # API routers (auths, chats, models, ...)
│       ├── models/             # SQLAlchemy models
│       ├── internal/
│       │   ├── db.py           # DB engine + peewee-migrate Router
│       │   └── migrations/     # Peewee migrations (001..0xx)
│       ├── migrations/versions/# Alembic migrations (15 files)
│       ├── retrieval/          # RAG, web loaders, vector DB adapters
│       ├── socket/             # Socket.IO
│       └── static/             # Backend-served /static (favicons, swagger-ui)
├── Dockerfile                  # Multi-stage: node:22 build -> python:3.11 runtime
├── docker-compose.yaml         # Primary compose file (ollama + open-webui)
├── docker-compose.*.yaml       # Variants: gpu, amdgpu, api, data, playwright
├── run-compose.sh              # Helper script (Linux/macOS)
├── pyproject.toml / uv.lock    # Python metadata + lock
├── package.json / package-lock.json
├── .env.example                # Env template (copied to .env as needed)
├── BRANDING_AUDIT.md           # (added) branding inventory
├── BASELINE.md                 # (added) recorded baseline
└── LOCAL_SETUP.md              # (this file)
```

---

## 5. Installation steps

### 5.1 Clone at the exact version

```bash
git clone --branch v0.6.5 --depth 50 https://github.com/open-webui/open-webui.git D:\open-webui
cd D:\open-webui
git describe --tags --always        # expect: v0.6.5
git log -1 --oneline                # expect: 07d84601 ...
```

### 5.2 Create the baseline branch

```bash
git switch -c custom-branding-v0.6.5
git status                          # clean, on custom-branding-v0.6.5
```

### 5.3 (Optional) Create an environment file

`.env` is git-ignored, so it never dirties the tree.

```bash
copy .env.example .env
```

`.env.example` contents:

```env
OLLAMA_BASE_URL='http://localhost:11434'
OPENAI_API_BASE_URL=''
OPENAI_API_KEY=''
SCARF_NO_ANALYTICS=true
DO_NOT_TRACK=true
ANONYMIZED_TELEMETRY=false
```

### 5.4 Build and start

```bash
docker compose up -d --build
```

First run downloads base images (`node:22-alpine3.20`, `python:3.11-slim-bookworm`,
`ollama/ollama`) and installs all frontend + backend dependencies. Expect
**20–40 minutes** and several GB of download on a first build.

> **Known failure without the Dockerfile fix:** `npm run build` → `vite build`
> dies with `FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap
> out of memory` (see §3). The added `ENV NODE_OPTIONS=--max-old-space-size=4096`
> is required on this machine and is already present in the working tree.

### 5.5 Verify

```bash
docker compose ps
curl http://localhost:3000/health     # {"status":true}
```

Then open <http://localhost:3000>.

---

## 6. Environment variables

Set in `docker-compose.yaml` (overridable via `.env`):

| Variable | Default in compose | Purpose |
| -------- | ------------------ | ------- |
| `OPEN_WEBUI_PORT` | `3000` | Host port mapped to container `8080` |
| `WEBUI_DOCKER_TAG` | `v0.6.5` | Image tag used for `io-agent:<tag>` |
| `OLLAMA_DOCKER_TAG` | `latest` | Ollama image tag |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Backend -> Ollama (inside the compose network) |
| `WEBUI_SECRET_KEY` | `""` (auto-generated) | JWT/session secret; auto-created as `/app/backend/data/.webui_secret_key` if empty |

Defined in the `Dockerfile` (runtime defaults):

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `PORT` | `8080` | Container listen port |
| `ENV` | `prod` (in image) | `dev` enables `/docs` and `/openapi.json` |
| `DOCKER` | `true` | Container flag |
| `WEBUI_BUILD_VERSION` | build hash | Build metadata |
| `WHISPER_MODEL` | `base` | Speech-to-text model |
| `RAG_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | RAG embeddings |
| `TIKTOKEN_ENCODING_NAME` | `cl100k_base` | Tokenizer |
| `SCARF_NO_ANALYTICS` / `DO_NOT_TRACK` / `ANONYMIZED_TELEMETRY` | `true`/`true`/`false` | Disable telemetry |

Important backend variables (**not** set in compose — defaults apply):

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `DATABASE_URL` | `sqlite:////app/backend/data/webui.db` | Database DSN (`postgresql://` supported) |
| `WEBUI_NAME` | `Io-agent` | Product name (see `REBRAND.md`) |
| `DATA_DIR` | `/app/backend/data` (in-container) | Data directory, bind to the volume |
| `ENABLE_SIGNUP` | enabled by default | First user becomes admin |

---

## 7. Docker commands

```bash
# Status
docker compose ps

# Logs (follow)
docker compose logs -f
docker compose logs -f open-webui

# Rebuild after source changes
docker compose up -d --build

# Rebuild without cache (clean build)
docker compose build --no-cache

# Shell into the app container
docker compose exec open-webui bash

# Inspect
docker inspect open-webui
docker volume ls
docker network ls
```

---

## 8. Docker Compose commands

```bash
# Start (build on first run)
docker compose up -d --build

# Start (reuse existing image)
docker compose up -d

# Stop (keeps containers and volumes)
docker compose stop

# Stop and remove containers (keeps volumes)
docker compose down

# Stop and remove containers + named volumes  -- DESTRUCTIVE
docker compose down -v

# Restart a single service
docker compose restart open-webui

# Re-run migrations by restarting the app
docker compose restart open-webui

# View resolved configuration
docker compose config
```

> Compose project name defaults to the directory name: **`open-webui`**.
> Resources are therefore named `open-webui-<service>` (containers) and
> `open-webui_<volume>` (volumes).

---

## 9. Application URL

| Surface | URL |
| ------- | --- |
| Web UI | **http://localhost:3000** |
| Health check | http://localhost:3000/health |
| API base | http://localhost:3000/api/v1 |
| Socket.IO | http://localhost:3000/socket.io |
| Swagger/OpenAPI docs | Not exposed (image runs `ENV=prod`; `docs_url=None`) |

First visit to <http://localhost:3000> presents the sign-up screen; the **first
registered account becomes the administrator**.

---

## 10. Container architecture

```
                 Host (Windows 11 + Docker Desktop / WSL2)
                 ┌──────────────────────────────────────────┐
  :3000 ─────────┼──► │ open-webui  :8080   (FastAPI + static) │
                 │         │  volume: open-webui_open-webui
                 │         │            -> /app/backend/data
                 │         ▼
                 │   (default bridge network "open-webui_default")
                 │         │
                 │         ├──► ollama :11434  (service "ollama")
                 │         │      volume: ollama -> /root/.ollama
                 │         │
                 │         └──► SQLite file at /app/backend/data/webui.db
                 └──────────────────────────────────────────┘
```

| Aspect | Detail |
| ------ | ------ |
| Application container | `io-agent` (service `open-webui`) |
| Image | Built locally from `Dockerfile` → tagged `io-agent:v0.6.5` (override with `WEBUI_DOCKER_TAG`) |
| Base stages | `node:22-alpine3.20` (frontend build) → `python:3.11-slim-bookworm` (runtime) |
| Entrypoint | `bash start.sh` → `uvicorn open_webui.main:app --host 0.0.0.0 --port 8080` |
| LLM sidecar | `ollama` (service `ollama`, `ollama/ollama:latest`) |
| Database container | **None** — SQLite embedded in the app container (see §13) |
| Redis | **Not used** by default compose (`redis` is optional, via `REDIS_URL`) |
| Health check | `curl -sf http://localhost:8080/health \| jq -e '.status == true'` |
| Restart policy | `unless-stopped` |

### Ports

| Host | Container | Protocol | Service |
| ---- | --------- | -------- | ------- |
| 3000 | 8080 | TCP | open-webui |
| 11434 (host process) | — | TCP | Host-side Ollama (outside compose, if running) |

> The compose `ollama` service does **not** publish a host port, so there is no
> conflict with a host Ollama already listening on `127.0.0.1:11434`.

### Volumes

| Volume | Mount point | Purpose |
| ------ | ----------- | ------- |
| `open-webui_open-webui` | `/app/backend/data` | `webui.db`, uploads, vector DB, model caches |
| `ollama` | `/root/.ollama` | Ollama model storage |

### Networks

| Network | Driver | Members |
| ------- | ------ | ------- |
| `open-webui_default` | bridge | `open-webui`, `ollama` |

---

## 11. Database configuration

| Item | Value |
| ---- | ----- |
| Engine | **SQLite** (default) |
| Location in container | `/app/backend/data/webui.db` |
| On host | Inside the `open-webui_open-webui` Docker volume |
| DSN | `sqlite:////app/backend/data/webui.db` |
| Config source | `backend/open_webui/env.py:265` |

Supported alternatives (not used in this baseline): set `DATABASE_URL` to
`postgresql://...` or `mysql://...` — `env.py` rewrites `postgres://` →
`postgresql://` automatically. PostgreSQL requires a separate database container
and the `DATABASE_URL` variable (a `litellm-postgres` container from an unrelated
project exists on this machine but is **not** part of this stack).

### Migration mechanism

The backend runs **two** migration systems in sequence:

1. **peewee-migrate** — `backend/open_webui/internal/db.py:59`
   `Router(db, migrate_dir=.../internal/migrations).run()`
   Runs at import time via `handle_peewee_migration(DATABASE_URL)`.
   Files: `backend/open_webui/internal/migrations/001_*.py … 0xx_*.py`
2. **Alembic** — `backend/open_webui/config.py:49-62`
   `command.upgrade(alembic_cfg, "head")`
   Files: `backend/open_webui/migrations/versions/` (15 revisions)
   Config: `backend/open_webui/alembic.ini`

Both run automatically on application startup — no manual migration command is
required for the baseline.

---

## 12. Static files

| Mount | Source | Contents |
| ----- | ------ | -------- |
| `/static` | `backend/open_webui/static/` | favicons, splash, PWA icons, `logo.png`, swagger-ui |
| `/cache` | `backend/data/cache/` | model/whisper/tiktoken caches |
| `/` (SPA) | `build/` (frontend, baked into image) | SvelteKit static adapter output |

Frontend static assets are authored in `static/` and copied into the build by
Vite; the backend serves its own copy from `backend/open_webui/static/`.
**Both copies must be treated as one unit during rebranding.**

---

## 13. Troubleshooting

| Symptom | Cause | Fix |
| ------- | ----- | ----- |
| `port is already allocated` / `Address already in use: 3000` | Another container or process holds port 3000 | `docker ps` to find it; `docker rm -f <name>`, or set `OPEN_WEBUI_PORT=3001` |
| `container name "io-agent" is already in use` | A pre-existing container uses that name | `docker rm -f io-agent` (volume is preserved) |
| `docker: permission denied` / daemon not running | Docker Desktop not started | Start Docker Desktop, wait for it to be ready |
| `failed to solve: frontend dockerfile` / build errors | Stale build cache | `docker compose build --no-cache` |
| Build slow or fails on npm step | Network / registry issue | Retry; optionally configure a registry mirror in `.npmrc` |
| Container unhealthy, `health` returns non-200 | App still starting or crashed | `docker compose logs -f open-webui` |
| `Frontend build directory not found` in logs | Frontend stage did not produce `build/` | Rebuild: `docker compose build --no-cache open-webui` |
| Login loop / invalid session after rebuild | `WEBUI_SECRET_KEY` regenerated | Set `WEBUI_SECRET_KEY` explicitly in `.env` |
| `database is locked` | Concurrent SQLite access | Reduce `UVICORN_WORKERS` to `1` (default) |
| Data missing after `down -v` | Volumes deleted | Expected — `-v` removes named volumes |
| Wrong version running | Stale image | `docker compose up -d --build` and verify `git log -1` |
| `FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory` during build | Node's default V8 heap cap is only 2096 MB with this VM's memory, but `vite build` needs more | Already fixed: `ENV NODE_OPTIONS=--max-old-space-size=4096` in the `Dockerfile` build stage (see §3). Revert only if you also raise Docker Desktop memory |
| WSL2 out of memory during build | Build too heavy | Raise WSL memory in `%USERPROFILE%\.wslconfig`, then `wsl --shutdown` |
| PowerShell shows "error" on git clone | git writes progress to stderr | Harmless — verify with `git log -1` |

---

## 14. How to stop the application

```bash
cd D:\open-webui
docker compose stop          # stop, containers retained (fast restart)
# or
docker compose down          # stop and remove containers (volumes retained)
```

---

## 15. How to start it again

```bash
cd D:\open-webui
docker compose up -d         # normal start (image already built)
docker compose ps            # verify running
curl http://localhost:3000/health
```

After source changes:

```bash
docker compose up -d --build
```

---

## 16. Completely remove / recreate the environment

```bash
cd D:\open-webui

# 1. Remove containers AND named volumes  (DESTROYS webui.db and uploads)
docker compose down -v

# 2. Remove the locally built image
docker image rm io-agent:v0.6.5

# 3. Optional: reclaim build cache
docker builder prune -f
docker image prune -f

# 4. Recreate from scratch
docker compose up -d --build
```

To keep the database when recreating, **omit `-v`**:

```bash
docker compose down
docker compose up -d --build
```

Full nuclear option (affects *all* Docker data on the machine, including
unrelated projects):

```bash
docker system prune -af --volumes      # DESTRUCTIVE — use with care
```

Re-cloning the repository:

```bash
# from D:\
git clone --branch v0.6.5 --depth 50 https://github.com/open-webui/open-webui.git D:\open-webui
cd D:\open-webui
git switch -c custom-branding-v0.6.5
docker compose up -d --build
```

---

## 17. Git hygiene

`git status` stays clean because these are git-ignored:

- `build/`, `node_modules/`, `.svelte-kit/` — generated frontend output
- `.env`, `.env.*` — local environment
- `backend/data/*` — runtime data
- `*.db` — SQLite database
- `build.log` — local `docker compose up -d --build` output

Expected state after baseline setup:

```
 M Dockerfile              # the single documented deviation (§3)
?? BRANDING_AUDIT.md       # added doc
?? LOCAL_SETUP.md          # added doc
?? BASELINE.md             # added doc
```

No other tracked file is modified. Only intentional documentation files
(`LOCAL_SETUP.md`, `BASELINE.md`, `BRANDING_AUDIT.md`) appear as untracked
additions.
