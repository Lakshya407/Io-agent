#!/usr/bin/env python3
"""
branding/rebrand_text.py

Mechanical text rebrand:  "Open WebUI"  ->  "Io-agent"

Touches only human-visible strings:
    src/**/*.svelte, *.ts, *.html
    src/lib/i18n/locales/**/translation.json   (keys AND values, all 54 locales)
    backend/**/*.py

PROTECTED (never rewritten):
    the BSD-3-Clause copyright notice on the About page, because licence
    compliance requires reproducing the original copyright holder verbatim.

Usage:  python branding/rebrand_text.py
"""

from __future__ import annotations

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Copyright notice that must survive the rebrand (BSD-3-Clause).
COPYRIGHT = "Open WebUI (Timothy Jaeryang Baek)"
PLACEHOLDER = "\x00BSD3COPYRIGHT\x00"

OLD = "Open WebUI"
NEW = "Io-agent"

# camelCase upstream handle, only meaningful inside translation payloads
OLD_CAMEL = "OpenWebUI"


def source_files() -> list[str]:
    out: list[str] = []
    for root, _dirs, files in os.walk(os.path.join(REPO, "src")):
        if os.path.join("i18n", "locales") in root:
            for f in files:
                if f == "translation.json":
                    out.append(os.path.join(root, f))
            continue
        for f in files:
            if f.endswith((".svelte", ".ts", ".html")):
                out.append(os.path.join(root, f))

    for root, _dirs, files in os.walk(os.path.join(REPO, "backend")):
        if "node_modules" in root or "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".py"):
                out.append(os.path.join(root, f))
    return sorted(out)


def process(path: str) -> list[str]:
    with open(path, encoding="utf-8") as fh:
        original = fh.read()

    text = original
    protected = COPYRIGHT in text
    if protected:
        text = text.replace(COPYRIGHT, PLACEHOLDER)

    text = text.replace(OLD, NEW)
    if path.endswith("translation.json"):
        text = text.replace(OLD_CAMEL, NEW)

    if protected:
        text = text.replace(PLACEHOLDER, COPYRIGHT)

    if text == original:
        return []

    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)

    # report which lines changed
    before = original.splitlines()
    after = text.splitlines()
    changed = []
    if len(before) == len(after):
        for i, (a, b) in enumerate(zip(before, after), start=1):
            if a != b:
                changed.append(f"    L{i}: {a.strip()[:90]}")
    else:
        changed.append("    (line count changed)")
    return changed


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    files = source_files()
    print(f"Scanning {len(files)} files\n")
    touched = 0
    lines = 0
    for path in files:
        ch = process(path)
        if ch:
            touched += 1
            lines += len(ch)
            print(f"{os.path.relpath(path, REPO)}")
            for c in ch:
                print(c)
    print(f"\nReplaced in {touched} files / {lines} lines.")
    print(f"'{OLD}' remaining (should be the BSD-3 notice only):")

    remaining = 0
    for path in files:
        with open(path, encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                if OLD in line:
                    remaining += 1
                    print(f"    {os.path.relpath(path, REPO)}:{i}: {line.strip()[:100]}")
    if remaining == 0:
        print("    (none)")


if __name__ == "__main__":
    main()
