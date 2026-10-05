# BASELINE.md — Verified Baseline for Open WebUI v0.6.5

> Status: **PASSED** — unmodified upstream `v0.6.5` built from source and running
> locally, verified on 2026-10-04.
> Purpose: this document records exactly what "working" looks like **before** any
> branding, vLLM, SSO, or RAG work begins, so any later regression can be
> detected against it.
> Companions: `LOCAL_SETUP.md` (how to run it), `BRANDING_AUDIT.md` (what to
> change next).

---

## 1. Identity of this baseline

| Field | Value |
| ----- | ----- |
| Repository | https://github.com/open-webui/open-webui |
| Tag | **`v0.6.5`** (exact; not `main`, not `v0.6.6+`) |
| Commit | `07d8460126a686de9a99e2662d06106e22c3f6b6` |
| `git log -1` | `07d84601 Merge pull request #12809 from open-webui/dev` |
| `git describe --tags --always` | `v0.6.5` |
| Branch | `custom-branding-v0.6.5` (created from the tag) |
| Clone path | `D:\open-webui` |
| Install method | **Built from source** via `docker compose up -d --build` |
| App version shown in logs | `v0.6.5` (ASCII banner on startup) |
| Frontend framework | SvelteKit + Vite 5.4.15, static adapter |
| Backend framework | FastAPI 0.115.7 on Python 3.11 (in-container) |

Verification commands:

```bash
git describe --tags --always   # v0.6.5
git log -1 --oneline           # 07d84601 Merge pull request #12809 from open-webui/dev
docker compose ps              # open-webui ... (healthy)
curl http://localhost:3000/health   # {"status":true}
```

---

## 2. Toolchain versions (host)

| Tool | Version |
| ---- | ------- |
| OS | Windows 11 Pro 10.0.26200, x64 |
| CPU | 11th Gen Intel i5-11320H, 4 cores / 8 threads |
| RAM | 15.8 GB total |
| Docker Desktop | 29.8.1 |
| Docker Compose | v5.5.1 |
| Docker VM memory | **7.65 GB** (default; no `.wslconfig`, no settings override) |
| Git | 2.55.0.windows.5 |
| Node (host, unused) | v22.23.3, npm 10.9.9 |
| Python (host, unused) | 3.14.6 — **outside** supported `>=3.11,<3.13`; container supplies 3.11 |

---

## 3. Images

| Image | Tag | Size | Source |
| ----- | --- | ---- | ------ |
| `ghcr.io/open-webui/open-webui` | `main` | 6.51 GB | **Built locally** from this repo's `Dockerfile` (tag forced by compose default `WEBUI_DOCKER_TAG=main`) |
| `ollama/ollama` | `latest` | 9.37 GB | Pulled from Docker Hub |
| `ghcr.io/open-webui/open-webui` | `v0.6.5` | 6.37 GB | Pre-existing (prebuilt) — retained, **not used** by this stack |

Build stages: `node:22-alpine3.20` (frontend) → `python:3.11-slim-bookworm`
(runtime, CPU wheels: `torch/torchvision/torchaudio` from
`download.pytorch.org/whl/cpu`).

---

## 4. Containers

`docker compose ps` at baseline:

```
NAME         IMAGE                                COMMAND               SERVICE      STATUS                     PORTS
ollama       ollama/ollama:latest                 "/bin/ollama serve"   ollama       Up                         11434/tcp
open-webui   ghcr.io/open-webui/open-webui:main   "bash start.sh"       open-webui   Up (healthy)               0.0.0.0:3000->8080/tcp
```

| Property | Value |
| -------- | ----- |
| Container name | `open-webui` |
| Command | `bash start.sh` → `uvicorn open_webui.main:app --host 0.0.0.0 --port 8080` |
| State | `running`, Docker healthcheck **`healthy`** |
| Health probe | `curl -sf http://localhost:8080/health \| jq -ne 'input.status == true'` |
| Entrypoint start time | `2026-10-04T14:08:20Z`; ready ≈ 40 s after start (embedding model + migrations) |
| Restart policy | `unless-stopped` |
| Sidecar | `ollama` (service `ollama`), no host port published |

> Startup note: during the first ~60 s the healthcheck reports `health: starting`
> then briefly `unhealthy` — `curl` gets an empty reply because uvicorn has not
> bound `:8080` yet, and `jq`'s `input` on empty stdin prints
> `jq: error (at <stdin>): break`. This is **expected startup behaviour**, not a
> defect: it self-corrects to `healthy` once the app binds (verified below).

Unrelated container present on the machine (not part of this stack):
`litellm-postgres` — `Exited (255)`.

---

## 5. Ports

| Host | Container | Service | Notes |
| ---- | --------- | ------- | ----- |
| `3000/tcp` | `8080/tcp` | open-webui | Web UI, health, API |
| *(none)* | `11434/tcp` | ollama | Internal only; no conflict with the host-side Ollama on `127.0.0.1:11434` |

---

## 6. Volumes

| Volume | Mount | Contents |
| ------ | ----- | -------- |
| `open-webui_open-webui` | `/app/backend/data` | `webui.db` (SQLite), `.webui_secret_key`, uploads, vector store |
| `open-webui_ollama` | `/root/.ollama` | Ollama model storage (empty — no models pulled) |
| `open-webui` | *(legacy)* | **Preserved from the pre-existing v0.6.5 container; not mounted by this stack** |

Network: `open-webui_default` (bridge) — members `open-webui`, `ollama`.

The database was created fresh by this build: both migration systems ran
automatically on first boot —

- **peewee-migrate** (`internal/migrations/`)
- **Alembic** — 15 revisions from `-> 7e5b5dc7342b, init` through
  `7826ab40b532, Update file table` to `3781e22d8b01, Update message & channel tables`

---

## 7. Environment

| Variable | Value at baseline | Source |
| -------- | ----------------- | ------ |
| `OPEN_WEBUI_PORT` | `3000` | compose default |
| `WEBUI_DOCKER_TAG` | `main` | compose default (drives the local build tag) |
| `OLLAMA_DOCKER_TAG` | `latest` | compose default |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | compose |
| `WEBUI_SECRET_KEY` | auto-generated → `/app/backend/data/.webui_secret_key` | runtime |
| `PORT` / `ENV` / `DOCKER` | `8080` / `prod` / `true` | Dockerfile |
| `RAG_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Dockerfile (downloaded at build) |
| `WHISPER_MODEL` / `TIKTOKEN_ENCODING_NAME` | `base` / `cl100k_base` | Dockerfile |
| `DATABASE_URL` | *(unset)* → `sqlite:////app/backend/data/webui.db` | default in `env.py` |
| `WEBUI_NAME` | *(unset)* → `Open WebUI` | default |
| Telemetry | `SCARF_NO_ANALYTICS=true`, `DO_NOT_TRACK=true`, `ANONYMIZED_TELEMETRY=false` | Dockerfile |
| `.env` | **not created** (not needed for baseline) | — |

---

## 8. Functional test results

| # | Test | Method | Result |
| - | ---- | ------ | ------ |
| 1 | Health endpoint | `GET /health` | **PASS** — `{"status":true}` |
| 2 | DB health | `GET /health/db` | **PASS** — `{"status":true}` |
| 3 | Web UI serves | `GET /` | **PASS** — HTTP 200, 7497 bytes, 1.59 s |
| 4 | Page title | `<title>` of `/` | **PASS** — `Open WebUI` |
| 5 | Branding strings present | HTML contains `Open WebUI` | **PASS** — yes (as expected for stock upstream) |
| 6 | First-user registration | `POST /api/v1/auths/signup` | **PASS** — user created, JWT issued (141 chars) |
| 7 | First user is admin | `GET /api/v1/auths/` with token | **PASS** — `role=admin` |
| 8 | Session auth | Bearer token accepted on API | **PASS** |
| 9 | Admin users list | `GET /api/v1/users/` | **PASS** — count = 1 |
| 10 | Chat store | `GET /api/v1/chats/` | **PASS** — count = 0 (empty, as expected) |
| 11 | Model list | `GET /api/v1/models/` | **PASS (expected empty)** — count = 0, no LLM backend configured |
| 12 | Migrations | startup logs | **PASS** — peewee + Alembic, no errors |
| 13 | Docker healthcheck | `docker inspect` | **PASS** — `healthy`; manual probe returns `true` |
| 14 | Container logs | `docker logs open-webui` | **PASS** — v0.6.5 banner, no tracebacks / ERRORs in app code |
| 15 | LLM chat round-trip | — | **SKIPPED (expected)** — no model pulled, per plan: do not integrate an LLM during baseline |
| 16 | Browser sign-in / UI interaction | — | **NOT AUTOMATED** — API-level auth verified; visual UI check left for human review at <http://localhost:3000> |

Test account created by test #6 (baseline environment only):

- email `baseline@local.test` / name `Baseline Admin` / password `Baseline-Test-2026!`
- role `admin`, id `ba4a3eca-2939-416c-b497-698e2f894c01`

> These credentials exist only in the local SQLite volume
> `open-webui_open-webui`. They can be deleted from **Admin → Settings → Users**,
> or by `docker compose down -v` + rebuild (which destroys the DB).

---

## 9. Deviations from upstream

Exactly **one** tracked file differs from `v0.6.5`:

```console
$ git diff --stat HEAD
 Dockerfile | 10 ++++++++++
 1 file changed, 10 insertions(+)
```

| Item | Detail |
| ---- | ------ |
| File / location | `Dockerfile`, frontend `build` stage, formerly line 34 `RUN npm run build` |
| Original (upstream) | `COPY . .` / `ENV APP_BUILD_HASH=${BUILD_HASH}` / `RUN npm run build` |
| Changed to | same, plus a commented block and `ENV NODE_OPTIONS=--max-old-space-size=4096` before `RUN npm run build` |
| Type | **Build-environment accommodation** — not a dependency change, not a functional change |
| Reason | Docker VM has 7.65 GB ⇒ Node's default V8 heap cap in the build container = 2096 MB (measured: 1 g→524 MB, 2 g→1048 MB, 3 g→1584 MB, 4 g/unlimited→2096 MB). `vite build` of this project needs >2096 MB and aborts with `FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory` |
| Runtime impact | **None** — `ENV` is confined to the `build` stage; the `base` runtime stage is a separate `FROM` |
| Dependency changes | **Zero.** `package.json`, `package-lock.json`, `backend/requirements.txt`, `pyproject.toml`, `uv.lock` all untouched |
| Revert path | `git checkout -- Dockerfile` (build will OOM again unless Docker Desktop memory is raised instead) |

No branding, UI, CSS, text, auth, RAG, or configuration changes were made.

Untracked additions (documentation only): `LOCAL_SETUP.md`, `BASELINE.md`,
`BRANDING_AUDIT.md`. `build.log` is git-ignored.

---

## 10. Warnings and observations

Log/runtime warnings observed — all **expected for stock upstream**, none block
operation:

| Warning | Where | Assessment |
| ------- | ----- | ---------- |
| `CORS_ALLOW_ORIGIN IS SET TO '*' - NOT RECOMMENDED FOR PRODUCTION` | `open_webui.env` | Default compose config; tighten before real deployment |
| `RequestsDependencyWarning: urllib3 (2.8.0) or chardet ... doesn't match a supported version` | Python startup | Upstream `requirements.txt` pin mismatch; harmless, cosmetic |
| `Failed to send telemetry event ClientStartEvent` (chromadb/posthog) | chromadb | Telemetry intentionally disabled; harmless |
| `USER_AGENT environment variable not set` | langchain | Cosmetic; upstream default |
| `grpcio < 1.83.0 does not support Post-Quantum Cryptography` (google-auth) | startup | Forward-looking deprecation notice (April 2027); not actionable at v0.6.5 |
| `Some chunks are larger than 500 kB after minification` | `vite build` | Upstream code-splitting warning; not a defect |
| Healthcheck `unhealthy` for the first ~60 s | container start | Expected while uvicorn boots (see §4) |
| Pre-existing prebuilt image `ghcr.io/open-webui/open-webui:v0.6.5` (6.37 GB) | host | Left in place; unused. Remove later to reclaim disk if desired |
| Legacy volume `open-webui` | host | Preserved per earlier decision; not mounted by this stack |

Security/operational baseline notes:

- No `.env` file exists; JWT secret is auto-generated and stored in the volume —
  setting `WEBUI_SECRET_KEY` explicitly is recommended before any persistent use.
- API docs (`/docs`, `/openapi.json`) are disabled because the image runs `ENV=prod`.
- SQLite is the datastore; no DB container, no Redis.

---

## 11. Baseline snapshot commands

Re-verify the baseline at any time:

```bash
cd D:\open-webui
git describe --tags --always        # v0.6.5
git diff --stat HEAD                # Dockerfile only, +10 lines
docker compose ps                   # open-webui (healthy), ollama
curl http://localhost:3000/health   # {"status":true}
curl http://localhost:3000/health/db# {"status":true}
docker logs open-webui 2>&1 | grep -i "error"   # expect no application errors
```

If any of these differ from §1, the baseline has drifted.
