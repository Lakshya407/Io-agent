# BRANDING_AUDIT.md — Open WebUI v0.6.5 White-Label Audit

> **Status: COMPLETE — rebrand executed.** See `REBRAND.md` for the change log.
> This document remains as the **pre-change inventory**: every location that
> carried Open WebUI branding, with the **original upstream v0.6.5 values**
> recorded before modification. Where a row says "to be changed", that change
> has now been made.
>
> - Repository: `D:\open-webui`
- Branch: `custom-branding-v0.6.5`
- Tag: `v0.6.5`
- Commit: `07d8460126a686de9a99e2662d06106e22c3f6b6`
- Audit date: 2026-10-04

---

## 1. How branding flows through the app

Understanding this prevents wasted effort later:

```
package.json "version": "0.6.5"  ──> hatch version ──> backend VERSION
                                                        │
backend/env.py  WEBUI_NAME (env var, default "Open WebUI") ──> /api/v1/configs/get_info
                                                        │                │
                                                        v                v
                        frontend src/lib/constants.ts APP_NAME   src/lib/stores WEBUI_NAME
                                                        │                │
                                                        └───────┬────────┘
                                                                v
                                          <title>, sidebar, login page, About,
                                          notification text, document title
```

Key mechanism found in `backend/open_webui/env.py:108-110`:

```python
WEBUI_NAME = os.environ.get("WEBUI_NAME", "Open WebUI")
if WEBUI_NAME != "Open WebUI":
    WEBUI_NAME += " (Open WebUI)"
```

**Important gotcha for the branding phase:** even if `WEBUI_NAME` is set to a custom
value, the backend *appends* `" (Open WebUI)"` unless the value is exactly
`"Open WebUI"`. This suffix must be removed during rebranding — otherwise the
product name leak persists regardless of configuration.

---

## 2. Master branding table

| # | Branding Element | File | Location | Current Value | Future Replacement |
| - | ---------------- | ---- | -------- | ------------- | ------------------ |
| 1 | Product name (frontend constant) | `src/lib/constants.ts` | line 4 | `export const APP_NAME = 'Open WebUI';` | TBD |
| 2 | Product name (backend default) | `backend/open_webui/env.py` | line 108 | `os.environ.get("WEBUI_NAME", "Open WebUI")` | TBD |
| 3 | Forced " (Open WebUI)" suffix | `backend/open_webui/env.py` | lines 109-110 | `WEBUI_NAME += " (Open WebUI)"` | Remove suffix logic |
| 4 | Favicon URL constant | `backend/open_webui/env.py` | line 112 | `WEBUI_FAVICON_URL = "https://openwebui.com/favicon.png"` | Custom favicon URL |
| 5 | Browser tab title | `src/app.html` | line 104 | `<title>Open WebUI</title>` | TBD |
| 6 | Meta description | `src/app.html` | line 19 | `content="Open WebUI"` | TBD |
| 7 | Apple mobile app title | `src/app.html` | line 10 | `content="Open WebUI"` | TBD |
| 8 | OpenSearch title | `src/app.html` | line 23 | `title="Open WebUI"` | TBD |
| 9 | Splash / loading screen logo | `src/app.html` | lines ~180-200 | `src="/static/splash.png"` | Custom logo |
| 10 | Splash dark-mode logo | `src/app.html` | `setSplashImage()` | `/static/splash-dark.png` | Custom logo |
| 11 | OpenSearch description file | `static/opensearch.xml` | `<ShortName>`, `<Description>` | `Open WebUI` / `Search Open WebUI` | TBD |
| 12 | PWA manifest name | `static/static/site.webmanifest` | `name` | `"Open WebUI"` | TBD |
| 13 | PWA manifest short name | `static/static/site.webmanifest` | `short_name` | `"WebUI"` | TBD |
| 14 | PWA manifest (backend copy) | `backend/open_webui/static/site.webmanifest` | `name` / `short_name` | `"Open WebUI"` / `"WebUI"` | TBD |
| 15 | Login page title | `src/routes/auth/+page.svelte` | line 161 | `` `${$WEBUI_NAME}` `` | Driven by #1/#2 |
| 16 | Login page logo | `src/routes/auth/+page.svelte` | line 185 | `{WEBUI_BASE_URL}/static/splash.png` | Custom logo |
| 17 | Login page logo (dark fallback) | `src/routes/auth/+page.svelte` | line 130 | `/static/favicon-dark.png` | Custom favicon |
| 18 | Login page headings | `src/routes/auth/+page.svelte` | lines 203-235 | `Signing in to {{WEBUI_NAME}}`, `Sign in to {{WEBUI_NAME}}` | Driven by #1/#2 |
| 19 | Sidebar "New Chat" logo | `src/lib/components/layout/Sidebar.svelte` | ~line 530 | `{WEBUI_BASE_URL}/static/favicon.png` | Custom favicon |
| 20 | Document title in chat | `src/lib/components/chat/Chat.svelte` | lines 1922-1923 | `` `${...} | ${$WEBUI_NAME}` `` | Driven by #1/#2 |
| 21 | Notification title | `src/routes/+layout.svelte` | lines 264, 413 | `` `${title} | Open WebUI` `` | TBD |
| 22 | Channel page title | `src/lib/components/channel/Channel.svelte` | line 198 | `#{...} | Open WebUI` | TBD |
| 23 | About page name + version | `src/lib/components/chat/Settings/About.svelte` | line 50 | `{$WEBUI_NAME}` | Driven by #1/#2 |
| 24 | About page update link | `src/lib/components/chat/Settings/About.svelte` | line 62 | `https://github.com/open-webui/open-webui/releases/tag/...` | TBD (remove/disable) |
| 25 | About page social badges | `src/lib/components/chat/Settings/About.svelte` | lines ~134-150 | Discord / X / GitHub `OpenWebUI` badges | Remove or replace |
| 26 | About page copyright | `src/lib/components/chat/Settings/About.svelte` | line 154 | `Open WebUI (Timothy Jaeryang Baek)` + BSD-3 text | TBD (keep license text) |
| 27 | About page license branch condition | `src/lib/components/chat/Settings/About.svelte` | line 111 | `{#if !$WEBUI_NAME.includes('Open WebUI')}` | Update condition |
| 28 | FastAPI / OpenAPI docs title | `backend/open_webui/main.py` | line 440 | `title="Open WebUI"` | TBD |
| 29 | OpenAPI description | `backend/open_webui/main.py` | line 1438 | `"Open WebUI is an open, extensible..."` | TBD |
| 30 | CLI version banner | `backend/open_webui/__init__.py` | line 20 | `f"Open WebUI version: {VERSION}"` | TBD |
| 31 | HTTP client header | `backend/open_webui/routers/openai.py` | lines 220, 710 | `"X-Title": "Open WebUI"` | TBD |
| 32 | Backend error strings (many) | `backend/open_webui/routers/{openai,ollama,audio}.py` | ~30 occurrences | `"Open WebUI: Server Connection Error"` | TBD |
| 33 | SeXNG RAG bot user-agent | `backend/open_webui/retrieval/web/searxng.py` | line 70 | `"Open WebUI (https://github.com/open-webui/open-webui) RAG Bot"` | TBD |
| 34 | Plugin version-check message | `src/routes/(app)/admin/functions/{create,edit}/+page.svelte`, `src/routes/(app)/workspace/tools/{create,edit}/+page.svelte` | line ~25-28 | `'Open WebUI version (v{{OPEN_WEBUI_VERSION}}) is lower...'` | TBD |
| 35 | "Open WebUI Community" share toasts | `src/lib/components/chat/ShareChatModal.svelte`, `admin/Functions.svelte`, `admin/Evaluations/Feedbacks.svelte`, `workspace/{Models,Prompts,Tools}.svelte` | various | `Redirecting you to Open WebUI Community`, `Share to Open WebUI Community` | Remove/repoint |
| 36 | "Made by Open WebUI Community" | `workspace/{Models,Prompts,Tools}.svelte`, `admin/Functions.svelte` | various | `Made by Open WebUI Community` | TBD |
| 37 | Admin "General" help links | `src/lib/components/admin/Settings/General.svelte` | lines 139, 186, 209, 228, 253, 337, 339 | `openwebui.com` docs/support URLs | TBD |
| 38 | Chat Settings help link | `src/lib/components/chat/Settings/General.svelte` | line 282-285 | `Help us translate Open WebUI!` | TBD |
| 39 | Help menu links | `src/lib/components/layout/Help/HelpMenu.svelte` | line 41 | openwebui.com / GitHub links | TBD |
| 40 | Update notification toast | `src/lib/components/layout/UpdateInfoToast.svelte` | line 24 | openwebui.com release link | TBD |
| 41 | Chat placeholder branding | `src/lib/components/chat/{ChatPlaceholder,Placeholder}.svelte` | lines 107 / 172 | openwebui.com links | TBD |
| 42 | Import `APP_NAME` -> store | `src/lib/stores/index.ts` | lines 1, 10 | `writable(APP_NAME)` | Driven by #1 |
| 43 | Translation strings (en-US) | `src/lib/i18n/locales/en-US/translation.json` | 10 matching keys | `Open WebUI` in 10 strings | TBD |
| 44 | Translation strings (54 locales) | `src/lib/i18n/locales/*/translation.json` | 54 directories | `Open WebUI` across all locales | TBD |
| 45 | Config helper comments/URLs | `backend/open_webui/config.py` | lines 280, 289, 831 | `open-webui` GitHub URLs (OAuth docs, etc.) | Review only |
| 46 | Socket auth message | `backend/open_webui/socket/main.py` | lines 76, 81, 86 | `open-webui` references | Review only |
| 47 | Storage provider URL | `backend/open_webui/storage/provider.py` | line 174 | `open-webui` S3 example | Review only |
| 48 | PDF generator reference | `backend/open_webui/utils/pdf_generator.py` | line 111 | `open-webui` URL | Review only |

---

## 3. Asset inventory (logos, favicons, splash)

All are **binary image files** and will need to be replaced wholesale.

### Source of truth: `static/static/` (copied into the frontend build)

| File | Size (bytes) | Purpose |
| ---- | ------------ | ------- |
| `static/static/favicon.ico` | 15086 | Browser tab icon (classic) |
| `static/static/favicon.png` | 10655 | Primary favicon (sidebar + `<link>`) |
| `static/static/favicon.svg` | 14617 | SVG favicon |
| `static/static/favicon-dark.png` | 15919 | Dark-mode favicon / login logo fallback |
| `static/static/favicon-96x96.png` | 3826 | 96x96 favicon |
| `static/static/apple-touch-icon.png` | 7512 | iOS home-screen icon |
| `static/static/web-app-manifest-192x192.png` | 8349 | PWA icon 192 |
| `static/static/web-app-manifest-512x512.png` | 30105 | PWA icon 512 |
| `static/static/splash.png` | 5239 | Light splash screen + login logo |
| `static/static/splash-dark.png` | 5419 | Dark splash screen |
| `static/static/site.webmanifest` | 470 | PWA manifest |
| `static/static/loader.js` | 0 | (empty) |

### Backend-served static: `backend/open_webui/static/` (served at `/static`)

Contains the **same** set of favicons/splash/manifest **plus**:

| File | Size | Purpose |
| ---- | ---- | ------- |
| `backend/open_webui/static/logo.png` | 5367 | Logo used by backend-served pages |
| `backend/open_webui/static/swagger-ui/favicon.png` | — | Swagger UI icon (dev docs only) |

> **Note:** both copies must be replaced together, otherwise the login page and the
> sidebar can show different logos. `env.py` line 1486 mounts `/static` from
> `STATIC_DIR` = `backend/open_webui/static`.

### Third location, easy to miss: repo-root `static/`

| File | Size | Served at | Purpose |
| ---- | ---- | --------- | ------- |
| `static/favicon.png` | 10655 | `/favicon.png` | Favicon at the **site root** — read by the Arena model avatar (`config.py` `DEFAULT_ARENA_MODEL`), the Leaderboard fallback and the Arena model modal |

This is Vite's **publicDir**, so it is copied into `build/` and served at a path
that is *not* under `/static/`. It is therefore **not** covered by the two-dir
parity check, and it was **missed in the first pass** — it kept serving the
upstream Open WebUI mark after every other asset had been rebranded.

Fixed by having `branding/generate_assets.py` write it too, with two guards:
`branding/preflight.py` (repo-tree) and `branding/verify_rebrand.py` (served
bytes) both fail if it drifts from `static/static/favicon.png`.

### Other branding-adjacent assets

| Location | Notes |
| -------- | ----- |
| `static/assets/images/{adam,earth,galaxy,space}.jpg` | Generic images, no Open WebUI logo — no change needed |
| `static/assets/emojis/*.svg` | Twemoji (CC-BY 4.0) — keep, attribution required |
| `static/assets/fonts/*` | Fonts — no branding |
| `demo.gif` (4.3 MB) | Repo README asset only — not shipped in the image |
| `README.md`, `CHANGELOG.md`, `.github/*` | Documentation branding — not user-facing in-app |

---

## 4. Search results summary

```text
grep -Rni "Open WebUI"  -> hits in src/, backend/, static/, docs/, kubernetes/
grep -Rni "open-webui"  -> hits in backend config/env/socket/storage, .github, docs, kubernetes
grep -Rni "OpenWebUI"   -> hits in About.svelte social badges, X/Twitter handle
```

| Search pattern | User-facing (in-app) | Backend/API | Docs/infra only |
| -------------- | -------------------- | ----------- | --------------- |
| `Open WebUI` | **~40 locations** | ~35 locations | README, docs, kubernetes |
| `open-webui` | ~10 locations | config.py, env.py, socket, storage | .github, docs, kubernetes, Dockerfile image name |
| `OpenWebUI` | About.svelte badges, X handle | — | README, workflows |

### Grouped by effort

| Group | Count | Effort | Notes |
| ----- | ----- | ------ | ----- |
| **A. Single-point product name** | 2 | Low | `constants.ts:4` + `env.py:108` (+ remove line 109-110 suffix) |
| **B. Static assets** | 12 files × 2 dirs | Medium | Favicons, splash, PWA icons, manifest |
| **C. HTML head / titles** | ~8 | Low | `app.html`, `opensearch.xml`, `<title>` in 3 components |
| **D. Hardcoded literals in components** | ~25 | Medium | Notification, Channel title, About page |
| **E. Translation strings** | 10 keys × 54 locales | High volume | Only `en-US` needs editing; others optional |
| **F. Backend error strings** | ~30 | Low/Mechanical | `"Open WebUI: Server Connection Error"` |
| **G. External links / badges** | ~25 | Medium | Decide: remove, repoint, or keep |
| **H. Docker/CI metadata** | ~10 | Low | Image name, labels, workflows (out of runtime scope) |

---

## 5. Items that do NOT need changing (or need care)

| Item | Reason |
| ---- | ------ |
| `LICENSE` (BSD-3-Clause) | License text must be preserved even after rebranding |
| About page BSD-3 license block | Must retain copyright + license notice |
| Twemoji attribution | CC-BY 4.0 requires attribution |
| `pyproject.toml` `name = "open-webui"` | Python package identity; changing breaks `pip`/`uv` install and `importlib.metadata.version("open-webui")` at `env.py:125` |
| `package.json` `"name"` | Used by Vite `APP_VERSION` define; low user visibility |
| `backend/open_webui/` package dir name | Python import path — renaming breaks every import |
| `kubernetes/` manifests | Not used by our Docker Compose deployment |
| `.github/` workflows | Fork infrastructure, not user-facing |

> **Constraint reminder:** `pyproject.toml` `name` and the `open_webui` package
> directory are *functional* identifiers, not branding. Renaming them is a
> refactor with high breakage risk and must be evaluated separately (and
> explicitly approved) — it is out of scope for the white-label phase.

---

## 6. Recommended change order for the next phase (NOT started)

1. `src/lib/constants.ts` — `APP_NAME`
2. `backend/open_webui/env.py` — `WEBUI_NAME` default **and remove the `" (Open WebUI)"` suffix**
3. `src/app.html` — `<title>`, meta description, apple-mobile-web-app-title, OpenSearch title
4. Static assets — favicons, splash, PWA icons (both `static/static/` and `backend/open_webui/static/`)
5. `static/static/site.webmanifest` + backend copy — `name`, `short_name`
6. `static/opensearch.xml` — ShortName/Description
7. Hardcoded component literals — notification, Channel title, About page
8. Translation strings — `en-US` at minimum
9. Backend strings — OpenAPI title, `X-Title`, error messages
10. External links/badges — decision required from stakeholder
11. Docker image metadata (`Dockerfile` labels, image name)

---

## 7. Open questions — RESOLVED

| # | Question | Decision |
|---|---|---|
| 1 | New product name (and PWA short name)? | **Io-agent** (org: infoorigin). PWA `name`/`short_name` both `Io-agent`; theme/background `#171717`. |
| 2 | Keep or remove the `" (Open WebUI)"` suffix in `env.py`? | **Removed entirely.** The block appended the suffix to *any* custom name unless the value was exactly `Open WebUI`. |
| 3 | Community links (Discord/X/GitHub) — remove or repoint? | **Removed.** Badges, social links, docs links, sponsorship pitches and the openwebui.com share cards are gone or gated behind `ENABLE_COMMUNITY_SHARING=false`. |
| 4 | Must the BSD-3-Clause notice stay on the About page? | **Yes — retained verbatim.** Required when redistributing a modified binary. Twemoji CC-BY 4.0 attribution retained too. |
| 5 | New favicon/logo assets — who supplies them, and which sizes? | Supplied as `branding/io.png`; the full set is derived from it by `branding/generate_assets.py` (see `REBRAND.md` §2). |

**Execution completed** — see `REBRAND.md` for the change log and
`DEPLOYMENT.md` for the on-prem build. Verified by `branding/preflight.py`
(build gate) and `branding/verify_rebrand.py` (31/31 post-build checks).
