"""Pre-build validation for the Io-agent rebrand. Exit 0 = safe to build."""
import json
import os
import py_compile
import re
import sys

REPO = r"D:\open-webui"
LICENSE_LINE = "Open WebUI (Timothy Jaeryang Baek)"
problems = []


def ok(msg):
    print(f"  [ok]   {msg}")


def bad(msg):
    problems.append(msg)
    print(f"  [FAIL] {msg}")


# 1. Svelte block balance -------------------------------------------------
print("\n-- Svelte block balance --")
bad_files = 0
for root, dirs, files in os.walk(os.path.join(REPO, "src")):
    dirs[:] = [d for d in dirs if d not in ("node_modules", ".svelte-kit")]
    for f in files:
        if not f.endswith(".svelte"):
            continue
        p = os.path.join(root, f)
        src = open(p, encoding="utf-8").read()
        opens = len(re.findall(r"{#(if|each|await|key|snippet)", src))
        closes = len(re.findall(r"{/(if|each|await|key|snippet)}", src))
        if opens != closes:
            bad(f"{os.path.relpath(p, REPO)}: opens={opens} closes={closes}")
            bad_files += 1
if bad_files == 0:
    ok("all .svelte block tags balanced")

# 2. Locale JSON validity -------------------------------------------------
print("\n-- Locale JSON --")
n = 0
for root, dirs, files in os.walk(os.path.join(REPO, "src", "lib", "i18n", "locales")):
    for f in files:
        if f == "translation.json":
            n += 1
            p = os.path.join(root, f)
            try:
                json.load(open(p, encoding="utf-8"))
            except Exception as e:
                bad(f"{os.path.relpath(p, REPO)}: {e}")
if not any("translation.json" in x for x in problems):
    ok(f"{n} locale files parse as JSON")

# 3. Python syntax --------------------------------------------------------
print("\n-- Backend syntax --")
pyfiles = []
for root, dirs, files in os.walk(os.path.join(REPO, "backend")):
    dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules")]
    for f in files:
        if f.endswith(".py"):
            pyfiles.append(os.path.join(root, f))
n = 0
for p in pyfiles:
    try:
        with open(p, "rb") as fh:
            compile(fh.read(), p, "exec")
        n += 1
    except SyntaxError as e:
        bad(f"{os.path.relpath(p, REPO)}: {e}")
if not any("backend" in x for x in problems):
    ok(f"{n} backend python files compile")

# 4. Residual upstream name (excluding licence + docs) --------------------
print("\n-- Residual 'Open WebUI' in shipped source --")
found = []
for sub in ("src", "backend", "static"):
    for root, dirs, files in os.walk(os.path.join(REPO, sub)):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "__pycache__", ".svelte-kit")]
        for f in files:
            if f.endswith((".png", ".ico", ".jpg", ".svg", ".woff", ".woff2", ".ttf", ".pyc")):
                continue
            p = os.path.join(root, f)
            try:
                lines = open(p, encoding="utf-8").read().splitlines()
            except Exception:
                continue
            for i, l in enumerate(lines, 1):
                if "Open WebUI" in l and LICENSE_LINE not in l:
                    found.append(f"{os.path.relpath(p, REPO)}:{i}: {l.strip()[:90]}")
if found:
    for x in found:
        bad(x)
else:
    ok("none (only the BSD-3 notice retains it)")

# 5. Assets present in both static dirs ----------------------------------
print("\n-- Asset parity --")
A = os.path.join(REPO, "static", "static")
B = os.path.join(REPO, "backend", "open_webui", "static")
ASSETS = [
    "favicon.png", "favicon-dark.png", "favicon-96x96.png", "favicon.ico",
    "favicon.svg", "apple-touch-icon.png", "splash.png", "splash-dark.png",
    "web-app-manifest-192x192.png", "web-app-manifest-512x512.png",
    "site.webmanifest",
]
import hashlib


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


mismatch = []
for a in ASSETS:
    pa, pb = os.path.join(A, a), os.path.join(B, a)
    if not os.path.exists(pa) or not os.path.exists(pb):
        mismatch.append(f"{a}: missing")
    elif sha(pa) != sha(pb):
        mismatch.append(f"{a}: differs between dirs")
if mismatch:
    for m in mismatch:
        bad(m)
else:
    ok(f"{len(ASSETS)} assets present and identical in both dirs")
if os.path.exists(os.path.join(B, "logo.png")):
    ok("backend logo.png present")
else:
    bad("backend logo.png missing")

# repo-root static/ is Vite's publicDir -> it is what /favicon.png serves, and
# it is NOT covered by the two-dir parity loop above. It is where the upstream
# Open WebUI mark survived unnoticed, so pin it explicitly.
_root_fav = os.path.join(REPO, "static", "favicon.png")
if not os.path.exists(_root_fav):
    bad("static/favicon.png (repo root) missing")
elif sha(_root_fav) != sha(os.path.join(A, "favicon.png")):
    bad("static/favicon.png (repo root) differs from static/static/favicon.png")
else:
    ok("root static/favicon.png matches the io chip (no /favicon.png leak)")

# 6. Branding core values -------------------------------------------------
print("\n-- Core branding values --")
checks = [
    ("src/lib/constants.ts", "APP_NAME = 'Io-agent'"),
    ("backend/open_webui/env.py", 'WEBUI_NAME = os.environ.get("WEBUI_NAME", "Io-agent")'),
    ("backend/open_webui/env.py", 'WEBUI_FAVICON_URL = "/static/favicon.png"'),
    ("src/app.html", "<title>Io-agent</title>"),
    ("Dockerfile", 'WEBUI_NAME="Io-agent"'),
    ("Dockerfile", "ENABLE_COMMUNITY_SHARING=false"),
    ("docker-compose.yaml", "image: io-agent:"),
    ("static/manifest.json", '"name": "Io-agent"'),
    ("static/opensearch.xml", "<ShortName>Io-agent</ShortName>"),
]
for rel, needle in checks:
    p = os.path.join(REPO, rel)
    if not os.path.exists(p):
        bad(f"{rel}: file missing")
        continue
    txt = open(p, encoding="utf-8", errors="replace").read()
    if needle in txt:
        ok(f"{rel}: {needle}")
    else:
        bad(f"{rel}: expected {needle!r}")

# 7. Must-not-change guard -------------------------------------------------
print("\n-- Must-not-change guard --")
p = os.path.join(REPO, "pyproject.toml")
txt = open(p, encoding="utf-8").read()
if 'name = "open-webui"' in txt:
    ok('pyproject.toml name still "open-webui" (required by env.py version lookup)')
else:
    bad("pyproject.toml name was changed - importlib.metadata.version() will break")

# 8. Required attributions retained --------------------------------------
print("\n-- Required attributions --")
about = open(os.path.join(REPO, "src", "lib", "components", "chat", "Settings", "About.svelte"),
             encoding="utf-8").read()
for needle, why in [
    ("Open WebUI (Timothy Jaeryang Baek)", "BSD-3 copyright notice"),
    ("Twemoji", "Twemoji CC-BY 4.0 attribution"),
    ("creativecommons.org/licenses/by/4.0", "CC-BY 4.0 link"),
    ("All rights reserved", "BSD-3 text"),
]:
    if needle in about:
        ok(f"{why}: present")
    else:
        bad(f"{why}: MISSING from About.svelte")

print("\n" + "=" * 62)
if problems:
    print(f"{len(problems)} PROBLEM(S):")
    for x in problems:
        print("  -", x)
else:
    print("PREFLIGHT PASSED - safe to build")
print("=" * 62)
sys.exit(1 if problems else 0)
