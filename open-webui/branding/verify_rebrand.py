#!/usr/bin/env python3
"""
branding/verify_rebrand.py

Post-build acceptance tests for the Io-agent rebrand. Run against a live
container:

    python branding/verify_rebrand.py

Exit code 0 = every check passed, 1 = at least one failure.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("OWUI_BASE", "http://localhost:3000")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(REPO, "static", "static")

ADMIN_EMAIL = os.environ.get("OWUI_ADMIN_EMAIL", "baseline@local.test")
ADMIN_PASSWORD = os.environ.get("OWUI_ADMIN_PASSWORD", "Baseline-Test-2026!")

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name}" + (f"  ->  {detail}" if detail else ""))


def request(path: str, method: str = "GET", payload=None, token: str | None = None,
            cookie: str | None = None, timeout: int = 30):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if cookie:
        req.add_header("Cookie", cookie)
    body = json.dumps(payload).encode() if payload is not None else None
    try:
        with urllib.request.urlopen(req, body, timeout=timeout) as res:
            raw = res.read()
            return res.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def get_json(path: str, **kw):
    status, raw = request(path, **kw)
    try:
        return status, json.loads(raw)
    except Exception:
        return status, None


def wait_healthy(timeout: int = 180) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, raw = request("/health", timeout=5)
            if status == 200 and b"true" in raw.replace(b" ", b""):
                return True
        except Exception:
            pass
        time.sleep(3)
    return False


def main() -> int:
    print(f"Target: {BASE}\n")

    print("Waiting for container to become healthy...")
    if not wait_healthy():
        check("container healthy", False, "timed out waiting for /health")
        return report()
    check("container healthy", True)

    # ------------------------------------------------------------------
    # 1. Backend health
    # ------------------------------------------------------------------
    print("\n-- Backend health --")
    s, raw = request("/health")
    check("/health 200 + status true", s == 200 and b"true" in raw.replace(b" ", b""), f"HTTP {s}")

    s, raw = request("/health/db")
    check("/health/db 200 + status true", s == 200 and b"true" in raw.replace(b" ", b""), f"HTTP {s}")

    # ------------------------------------------------------------------
    # 2. Page title / no upstream name
    # ------------------------------------------------------------------
    print("\n-- HTML document --")
    s, raw = request("/")
    html = raw.decode("utf-8", "replace")
    check("GET / -> 200", s == 200, f"HTTP {s}, {len(raw)} bytes")
    check("title is Io-agent", "<title>Io-agent</title>" in html)
    check("meta description Io-agent", 'name="description" content="Io-agent"' in html)
    check("apple-mobile-web-app-title Io-agent", 'apple-mobile-web-app-title" content="Io-agent"' in html)
    upstream = [t for t in ("Open WebUI", "OpenWebUI", "openwebui.com") if t in html]
    check("no upstream name in HTML", not upstream, f"found: {upstream}" if upstream else "")

    # ------------------------------------------------------------------
    # 3. Static assets actually served are the rebranded ones
    # ------------------------------------------------------------------
    print("\n-- Static assets --")
    for name in (
        "favicon.png",
        "favicon-dark.png",
        "favicon-96x96.png",
        "favicon.ico",
        "favicon.svg",
        "apple-touch-icon.png",
        "splash.png",
        "splash-dark.png",
        "web-app-manifest-192x192.png",
        "web-app-manifest-512x512.png",
    ):
        local = os.path.join(ASSETS, name)
        s, raw = request(f"/static/{name}")
        if not os.path.exists(local):
            check(f"/static/{name}", False, "local source missing")
            continue
        with open(local, "rb") as fh:
            local_bytes = fh.read()
        same = s == 200 and raw == local_bytes
        check(
            f"/static/{name} matches generated asset",
            same,
            f"HTTP {s}, served {len(raw)} B vs local {len(local_bytes)} B",
        )

    # Repo-root static/favicon.png is Vite's publicDir, so it is what
    # /favicon.png serves. It lives OUTSIDE static/static/, so the loop above
    # cannot see it - and that is exactly where the upstream Open WebUI mark
    # survived. The Arena model, Leaderboard and Arena model modal read it.
    root_fav = os.path.join(REPO, "static", "favicon.png")
    s, raw = request("/favicon.png")
    if os.path.exists(root_fav):
        with open(root_fav, "rb") as fh:
            root_bytes = fh.read()
        check(
            "/favicon.png is the io chip (not the upstream mark)",
            s == 200 and raw == root_bytes,
            f"HTTP {s}, served {len(raw)} B vs local {len(root_bytes)} B",
        )
        check(
            "/favicon.png identical to /static/favicon.png",
            raw == request("/static/favicon.png")[1],
        )
    else:
        check("repo-root static/favicon.png exists", False, "file missing")

    # ------------------------------------------------------------------
    # 4. Manifests / opensearch
    # ------------------------------------------------------------------
    print("\n-- Manifests --")
    s, raw = request("/manifest.json")
    try:
        man = json.loads(raw)
        check("/manifest.json name == Io-agent", s == 200 and man.get("name") == "Io-agent",
              str(man.get("name")))
        check("/manifest.json has icons", bool(man.get("icons")), f"{len(man.get('icons', []))} icons")
    except Exception as e:
        check("/manifest.json valid JSON", False, str(e))

    s, raw = request("/static/site.webmanifest")
    try:
        site = json.loads(raw)
        check("site.webmanifest name == Io-agent", site.get("name") == "Io-agent",
              f"name={site.get('name')!r} short={site.get('short_name')!r}")
    except Exception as e:
        check("site.webmanifest valid JSON", False, str(e))

    s, raw = request("/opensearch.xml")
    xml = raw.decode("utf-8", "replace")
    check("opensearch ShortName Io-agent", s == 200 and "<ShortName>Io-agent</ShortName>" in xml)
    check("opensearch free of upstream name", "Open WebUI" not in xml)

    # ------------------------------------------------------------------
    # 5. Sign in, then check API-level branding
    # ------------------------------------------------------------------
    print("\n-- API --")
    s, signin = get_json(
        "/api/v1/auths/signin",
        method="POST",
        payload={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    ok_signin = s == 200 and isinstance(signin, dict) and signin.get("token")
    check("admin sign-in", bool(ok_signin), f"HTTP {s}")
    if not ok_signin:
        return report()

    token = signin["token"]

    # /api/config only exposes the *features* block to an authenticated user,
    # and it authenticates from the login cookie rather than the bearer header.
    s, cfg = get_json("/api/config", cookie=f"token={token}")
    check("GET /api/config 200", s == 200, f"HTTP {s}")
    if isinstance(cfg, dict):
        name = cfg.get("name")
        check("config.name == Io-agent", name == "Io-agent", f"got {name!r}")

    # ------------------------------------------------------------------
    # 6. Flip ENABLE_COMMUNITY_SHARING in the DB if it is still True
    #    (the env default only applies to a fresh database)
    # ------------------------------------------------------------------
    s, admin_cfg = get_json("/api/v1/auths/admin/config", token=token)
    check("GET admin config", s == 200 and isinstance(admin_cfg, dict), f"HTTP {s}")
    if not isinstance(admin_cfg, dict):
        return report()

    if admin_cfg.get("ENABLE_COMMUNITY_SHARING"):
        print("\n-- Flipping ENABLE_COMMUNITY_SHARING in DB --")
        admin_cfg["ENABLE_COMMUNITY_SHARING"] = False
        s2, resp = request(
            "/api/v1/auths/admin/config", method="POST", payload=admin_cfg, token=token
        )
        check("admin config updated", s2 == 200, f"HTTP {s2}")
        time.sleep(1)
    else:
        print("\n(enable_community_sharing already False, no DB update needed)")

    s, cfg2 = get_json("/api/config", cookie=f"token={token}")
    sharing = (cfg2 or {}).get("features", {}).get("enable_community_sharing")
    check("enable_community_sharing is False", sharing is False, f"got {sharing!r}")

    # ------------------------------------------------------------------
    # 7. Functional regression
    # ------------------------------------------------------------------
    print("\n-- Functional regression --")
    s, users = get_json("/api/v1/users/", token=token)
    check("GET /api/v1/users/", s == 200, f"HTTP {s}, count={len(users) if isinstance(users, list) else '?'}")

    s, chats = get_json("/api/v1/chats/", token=token)
    check("GET /api/v1/chats/", s == 200, f"HTTP {s}")

    s, models = get_json("/api/v1/models/", token=token)
    check("GET /api/v1/models/", s == 200, f"HTTP {s}, count={len(models) if isinstance(models, list) else '?'}")

    return report()


def report() -> int:
    failed = [r for r in RESULTS if not r[1]]
    total = len(RESULTS)
    print("\n" + "=" * 62)
    print(f"{total - len(failed)}/{total} checks passed")
    if failed:
        print("FAILURES:")
        for name, _, detail in failed:
            print(f"  - {name}   {detail}")
    print("=" * 62)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
