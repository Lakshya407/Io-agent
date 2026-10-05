# DEPLOYMENT.md — Io-agent on your on-prem server

Target: **Linux x86_64, CPU only, server has internet access.**

---

## 0. Short answer to your question

> *"can I pull these changes onto my on-prem local server?"*

**Yes.** Every change lives in the working tree at `D:\open-webui` on branch
`custom-branding-v0.6.5`. Nothing is baked into your local machine only — the
image is *built from the source*, so all you have to move to the server is the
**source tree** (or a git remote), then run `docker compose build`.

Three ways to move it, pick whichever matches your environment:

| Method | Best when | Server needs |
|---|---|---|
| **A. Git remote** (recommended) | you have any Git server (GitLab/Gitea/GitHub/Codeberg) reachable from both machines | `git clone` |
| **B. `git bundle`** | no git server, but you can copy one file over | `git clone bundle` |
| **C. Zip archive** | simplest, no git at all on the server | unzip |

There is also a **fully offline** option (Docker image transfer) described in
**§6** — use it if the server is ever disconnected from the internet.

---

## 1. What changed vs. upstream

* Pinned to tag **`v0.6.5`** — commit `07d8460126a686de9a99e2662d06106e22c3f6b6`
* Branch: **`custom-branding-v0.6.5`**
* Branding: product name **Io-agent**, org **infoorigin**, logo/favicon/splash/PWA
  icons all replaced (derived from `branding/io.png`)
* Outbound Open WebUI community/docs links removed; BSD-3-Clause notice kept
  (legally required when redistributing a modified binary)
* Dependency versions are **unchanged** from `v0.6.5` — no upgrades were made

See `BRANDING_AUDIT.md` for the full inventory and `BASELINE.md` for the
verified pre-branding baseline.

---

## 2. Method A — Git remote (recommended)

**On your Windows machine (`D:\open-webui`):**

```powershell
cd D:\open-webui
git add -A
git commit -m "Rebrand Open WebUI v0.6.5 to Io-agent"
git remote add origin git@<your-git-server>:<org>/io-agent.git
git push -u origin custom-branding-v0.6.5
```

**On the server:**

```bash
git clone -b custom-branding-v0.6.5 git@<your-git-server>:<org>/io-agent.git
cd io-agent
docker compose up -d --build
```

---

## 3. Method B — `git bundle` (no git server needed)

One self-contained file that carries the full history.

**On Windows:**

```powershell
cd D:\open-webui
git bundle create io-agent.bundle custom-branding-v0.6.5
```

Copy `io-agent.bundle` to the server (scp/USB/shared folder).

**On the server:**

```bash
git clone -b custom-branding-v0.6.5 io-agent.bundle io-agent
cd io-agent
docker compose up -d --build
```

If you later get a real git remote, you can push from the bundle's history:

```bash
git remote add origin <your-git-server>:<org>/io-agent.git
git push -u origin custom-branding-v0.6.5
```

---

## 4. Method C — Zip archive

**On Windows** (PowerShell):

```powershell
cd D:\open-webui
git archive --format=zip -o io-agent-source.zip custom-branding-v0.6.5
```

> `git archive` is better than zipping the folder directly — it excludes
> `.git`, `node_modules`, and any build output, so you only ship tracked files.

**On the server:**

```bash
unzip io-agent-source.zip -d io-agent
cd io-agent
docker compose up -d --build
```

⚠️ With this method you lose git history on the server. That's fine for
deploying, but you won't be able to `git pull` future updates. Use A or B if
you plan to maintain a fork.

---

## 5. Build requirements on the server

| Requirement | Value |
|---|---|
| OS | Linux x86_64 (amd64) |
| Docker | 24+ with Compose v2 |
| RAM | **≥ 8 GB recommended** — the Vite frontend build needs ~4 GB (the `Dockerfile` sets `NODE_OPTIONS=--max-old-space-size=4096` for this) |
| Disk | ~10 GB free for build cache + image |
| Network | internet, to pull `python:3.11-slim-bookworm`, `node:22-alpine3.20`, `ollama/ollama` |
| GPU | none required (CPU build, no CUDA wheels) |

First build takes roughly 10–20 minutes; later builds are cached.

---

## 6. Fully offline transfer (optional)

If the server has **no** internet, build on Windows and ship the image:

**On Windows:**

```powershell
docker save io-agent:v0.6.5 | gzip -c > io-agent-v0.6.5.tar.gz
# ~2-3 GB compressed
```

**On the server:**

```bash
gunzip -c io-agent-v0.6.5.tar.gz | docker load
docker pull ollama/ollama        # only if not already present / still online
docker compose up -d             # no --build: image already exists
```

---

## 7. Configuration

The defaults in `docker-compose.yaml` work as-is. Optional `.env` file in the
project root to override:

```bash
# .env
OPEN_WEBUI_PORT=3000            # host port -> container 8080
WEBUI_DOCKER_TAG=v0.6.5         # image tag  -> io-agent:v0.6.5
OLLAMA_DOCKER_TAG=latest
```

Branding env vars are baked into the image (`Dockerfile`) but can be
overridden at runtime:

```bash
WEBUI_NAME=Io-agent             # visible product name
ENABLE_COMMUNITY_SHARING=false  # hides community/docs share cards
```

> **Note on `WEBUI_NAME`:** upstream `v0.6.5` appends `" (Open WebUI)"` to any
> custom name unless it is exactly `"Open WebUI"`. That suffix has been removed
> from `backend/open_webui/env.py`, so `WEBUI_NAME=Io-agent` renders exactly
> as `Io-agent`.

---

## 8. Run

```bash
docker compose up -d --build     # first time
docker compose ps                # wait for "healthy"
docker compose logs -f open-webui
```

Open `http://<server>:3000` and register the first account — the **first user
to sign up becomes the admin**.

```bash
# stop / restart / update
docker compose stop
docker compose start
docker compose up -d --build     # after pulling new source
```

---

## 9. Data & upgrades

| What | Where | Notes |
|---|---|---|
| App data (DB, uploads) | Docker volume `open-webui_open-webui` | **survives rebuilds** |
| Source | git / archive | rebrand is in the source tree |
| Image | `io-agent:v0.6.5` | rebuilt from source |

> The compose project name is derived from the **folder name**. Keep the
> folder named `io-agent` on the server, otherwise Docker creates a *new empty
> volume* and your data appears to vanish.

---

## 10. If you ever need GPU

This build is CPU-only. To add CUDA later:

1. Build with the GPU args (`USE_CUDA=true`, `USE_CUDA_VER=cu124`)
2. Swap the `ollama` service for the GPU variant in `docker-compose.yaml`
3. Rebuild — no source changes needed

---

## 11. Rollback

The upstream tag is untouched — you can always fall back:

```bash
git checkout v0.6.5              # pristine upstream source
docker compose up -d --build
# or simply:
docker pull ghcr.io/open-webui/open-webui:v0.6.5
```
