# REBRAND.md — Io-agent change log

What was changed to turn Open WebUI **v0.6.5** into **Io-agent** for **infoorigin**.

* Base tag: `v0.6.5` — commit `07d8460126a686de9a99e2662d06106e22c3f6b6`
* Branch: `custom-branding-v0.6.5`
* **119 files changed — 683 insertions(+), 872 deletions(-)**
* **No dependency versions were changed.** Every `requirements.txt` /
  `package.json` version is byte-identical to `v0.6.5`.

| Area | Files |
|---|---|
| Translation locales (all languages) | 53 |
| Svelte components / routes | 28 |
| Binary branding assets | 22 |
| Python backend | 8 |
| Config / HTML / manifests | 8 |
| **Total modified** | **119** |
| New files | `branding/`, `BASELINE.md`, `BRANDING_AUDIT.md`, `DEPLOYMENT.md`, `LOCAL_SETUP.md`, `REBRAND.md` |

---

## 1. Product name — single points of truth

| File | Change |
|---|---|
| `src/lib/constants.ts` | `APP_NAME = 'Io-agent'` |
| `backend/open_webui/env.py` | `WEBUI_NAME` default → `"Io-agent"` |
| `backend/open_webui/env.py` | **removed** the `" (Open WebUI)"` suffix block — upstream appends it to *any* custom name unless the value is exactly `Open WebUI` |
| `backend/open_webui/env.py` | `WEBUI_FAVICON_URL` → `/static/favicon.png` (was `https://openwebui.com/favicon.png`) |
| `Dockerfile` | `ENV WEBUI_NAME="Io-agent"` so the image carries the name by default |

Because `WEBUI_NAME` is now exactly `Io-agent`, the sidebar, login page, browser
tab, About panel, notifications, and OpenAPI title all inherit it.

### Hardcoded literals replaced

* `src/app.html` — `<title>`, meta `description`, `apple-mobile-web-app-title`,
  OpenSearch `title`
* `src/routes/+layout.svelte` — desktop + channel notification titles
  (`… | Io-agent`)
* `src/lib/components/channel/Channel.svelte` — channel page `<title>`
* `static/opensearch.xml` — `ShortName` / `Description`
* `static/manifest.json` — was an **empty `{}`**, now a real manifest
  (`name`, `short_name`, maskable icons, theme colour `#171717`)
* Both `site.webmanifest` copies — `name` / `short_name`
* `backend/open_webui/main.py` — OpenAPI `title`, `description`, startup banner
* `backend/open_webui/__init__.py` — CLI version banner
* `backend/open_webui/retrieval/web/searxng.py` — SearXNG bot `User-Agent`
* `backend/open_webui/routers/openai.py` — OpenRouter `X-Title`
* **21** `… Server Connection Error` strings across `audio.py`, `openai.py`,
  `ollama.py` → `Io-agent: Server Connection Error`
* `src/routes/error/+page.svelte` — "…Backend Required" uses `$WEBUI_NAME`

### i18n

A scripted rebrand rewrote **523 lines across 56 files**, replacing
`Open WebUI` → `Io-agent` in both **keys and values** for all **54 locales**
(plus the camelCase `OpenWebUI` handle in translated text). Keys and values
were changed together so existing translations keep resolving.

---

## 2. Logo, favicon & PWA assets

All generated from **`branding/io.png`** (the 2400×2729 white *io* wordmark) by
`branding/generate_assets.py`, written to **both** asset directories that must
stay in sync:

* `static/static/` (frontend)
* `backend/open_webui/static/` (mounted at `/static`)

The source glyph is **pure white on transparent**, which is invisible on light
backgrounds, so several treatments are derived. The chosen look for the app's
round chips (model avatars, the "New Chat" logo, the browser favicon) is a
**light disc with a dark glyph** — it reads clearly on both light and dark
app themes and matches what upstream shipped for the browser favicon:

| Variant | Used by |
|---|---|
| **White disc + dark glyph** (`#ffffff` / `#171717`) | `favicon.png`, `favicon-96x96.png`, `favicon.ico`, `favicon.svg`, repo-root `static/favicon.png` |
| **White tile (full bleed, maskable-safe) + dark glyph** | `apple-touch-icon.png`, `web-app-manifest-192x192.png`, `web-app-manifest-512x512.png`, `logo.png` |
| Dark disc + white glyph (`#171717` / `#ffffff`) | `favicon-dark.png` (dark-theme logo, used by the login & onboarding screens), `swagger-ui/favicon.png` (Swagger's page background is white) |
| Dark glyph, transparent (`#171717`) | `splash.png` — light-theme loading screen & login logo |
| White glyph, transparent | `splash-dark.png` — dark-theme loading screen & login logo |

Files produced (×2 directories, plus backend `logo.png`):

```
favicon.png  favicon-dark.png  favicon-96x96.png  favicon.ico  favicon.svg
apple-touch-icon.png  splash.png  splash-dark.png
web-app-manifest-192x192.png  web-app-manifest-512x512.png  site.webmanifest
```

Verified: glyphs are centred to the pixel, 56% of canvas for disc variants and
58% for glyph-only variants, and both directories are byte-identical.

### Repo-root `static/favicon.png` (the `/favicon.png` leak)

`static/` (repo root) is Vite's **publicDir**, so it is what the server returns
for `/favicon.png` — a path that is *not* under `/static/` and therefore outside
the two-dir parity check. Upstream ships an Open WebUI mark there, and it was
never rebranded: it is read by the **Arena model** avatar
(`config.py` `DEFAULT_ARENA_MODEL`), the **Leaderboard** fallback and the
**Arena model modal**. The generator now writes it too, and two guards keep it
from drifting back:

* `branding/preflight.py` — fails if root `static/favicon.png` differs from
  `static/static/favicon.png`
* `branding/verify_rebrand.py` — fails if the served `/favicon.png` differs from
  that file (i.e. if the upstream mark is being served again)

---

## 3. Outbound Open WebUI links removed

Per the decision *"remove links, keep license"*:

**Removed entirely**

* Help menu → *Documentation* item (`docs.openwebui.com`)
* About page → Discord / X / GitHub badges, release-version link,
  "Check for updates" button
* Admin Settings → Documentation link, three social badges, enterprise-license
  links, API-endpoints doc link
* Admin Users → >50-users sponsorship pitch (enterprise + GitHub Sponsors links)
* Error page → upstream README link **and** Discord invite
* Settings → Ollama troubleshooting link, translation CONTRIBUTING link
* Tools / Tool-servers → `openapi-servers` links
* Admin Evaluations → ungated "Share to … Community" leaderboard button
* `FunctionEditor` boilerplate → `author: infoorigin`
  (was `open-webui` + two `github.com/open-webui` URLs)
* Update toast → upstream releases link

**Neutered (no longer reachable)**

`ENABLE_COMMUNITY_SHARING=false` is set in the `Dockerfile`, which hides every
community share card, share button and model/prompt/tool discovery card. The 10
remaining `openwebui.com` references in source sit inside that gate (or are
`.includes()` URL-validation allowlists that are never rendered).

> **Note:** this is a `PersistentConfig`, so the *database* value wins over the
> environment variable once a config row exists. The Dockerfile default applies
> to **fresh** installs; on an existing database flip it once in
> **Admin → Settings → General → Enable community sharing** (or via
> `POST /api/v1/auths/admin/config`). `branding/verify_rebrand.py` does this
> automatically during verification.

---

## 4. Phone-home removed

`GET /api/version/updates` used to call
`https://api.github.com/repos/open-webui/open-webui/releases/latest` on **every
page load**, and a toast would then offer "a new version" linking to upstream
releases — meaningless for a pinned fork. It now returns
`{"current": VERSION, "latest": VERSION}` with no network call.

Also removed:

* `HTTP-Referer: https://openwebui.com/` sent to OpenRouter (kept `X-Title: Io-agent`)
* Startup ASCII banner spelling **OPEN WEBUI** → Io-agent / infoorigin banner

---

## 5. Deliberately NOT changed

| Thing | Why |
|---|---|
| `pyproject.toml` `name = "open-webui"` | `env.py` calls `importlib.metadata.version("open-webui")` — renaming breaks startup |
| `backend/open_webui/` package directory | same reason |
| `package.json` `name` | build tooling reads it |
| `X-OpenWebUI-*` HTTP headers | internal protocol identifiers shared by client and server; not user-facing |
| **BSD-3-Clause copyright notice** on About | redistribution of a modified binary **must** reproduce the original notice verbatim |
| Twemoji CC-BY 4.0 attribution | licence requirement |
| Third-party doc links (faster-whisper, SpeechT5, Twemoji, AUTOMATIC1111) | attributions for third-party components, not Open WebUI |
| Dependency versions | you asked for confirmation before any upgrade — none were made |

---

## 6. Tooling added (`branding/`)

| Script | Purpose |
|---|---|
| `generate_assets.py` | derives the whole icon set from `io.png` |
| `rebrand_text.py` | the `Open WebUI` → `Io-agent` codemod (protects the BSD-3 notice) |
| `preflight.py` | 8-category build gate: Svelte balance, locale JSON, Python syntax, asset parity (including repo-root `static/favicon.png`, the `/favicon.png` leak), core values, licence guard |
| `verify_rebrand.py` | post-build acceptance tests against the live container, incl. the bytes served at `/favicon.png` |

---

## 7. Verification

```bash
python branding/preflight.py      # before building
python branding/verify_rebrand.py # after building
```
