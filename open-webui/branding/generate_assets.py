#!/usr/bin/env python3
"""
branding/generate_assets.py
===========================

Derives the complete Io-agent favicon / splash / PWA icon set from a single
source logo, and writes it into BOTH static asset directories:

    static/static/                      (frontend, Vite static dir)
    backend/open_webui/static/          (backend, mounted at /static)

Source logo
    White "io" wordmark on a transparent background, e.g. 2400x2729 RGBA.
    The source also contains faint decorative rings; these are stripped by
    selecting only white + sufficiently opaque pixels.

Why there are several visual variants
    The source glyph is WHITE. White is invisible on a light background, so
    every asset is derived from the glyph in one of a few forms:

      white disc/tile + dark (#171717) glyph
                           -> the canonical "chip": browser favicon, the
                             sidebar "New Chat" logo, every model avatar that
                             has no image of its own, apple-touch-icon and the
                             maskable PWA tiles. A light chip reads clearly on
                             both light and dark app themes and matches what
                             upstream shipped for the browser favicon.
      dark (#171717) disc + white glyph
                           -> the dark-mode counterpart (favicon-dark.png) and
                             the Swagger UI favicon, which sits on Swagger's
                             white page background.
      glyph-only, dark     -> light-theme full-bleed art (splash.png)
      glyph-only, white    -> dark-theme full-bleed art (splash-dark.png)

    NOTE: repo-root static/favicon.png (served at /favicon.png) lives outside
    the two target dirs because it is Vite's publicDir. It must stay identical
    to static/static/favicon.png - preflight.py enforces that.

Usage
    python branding/generate_assets.py
"""

from __future__ import annotations

import base64
import io
import os
import shutil
import sys

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOURCE_LOGO_CANDIDATES = [
    os.path.join(REPO, "branding", "io.png"),
    r"C:\Users\Admin\Downloads\io.png",
]

TARGET_DIRS = [
    os.path.join(REPO, "static", "static"),
    os.path.join(REPO, "backend", "open_webui", "static"),
]

# Brand colour used for the dark tile / "black" glyph (matches app theme-color)
BRAND_DARK = (23, 23, 23)  # #171717
WHITE = (255, 255, 255)

# Glyph width as a fraction of the square canvas
GLYPH_W_TILE = 0.56      # tiled icons (favicon, logo)
GLYPH_W_MASKABLE = 0.54  # PWA maskable icons (must respect safe zone)
GLYPH_W_PLAIN = 0.58     # glyph-only variants (splash, dark favicon)

# ---------------------------------------------------------------------------
# Glyph extraction
# ---------------------------------------------------------------------------


def find_source() -> str:
    for p in SOURCE_LOGO_CANDIDATES:
        if os.path.exists(p):
            return p
    sys.exit("Source logo not found. Tried:\n  " + "\n  ".join(SOURCE_LOGO_CANDIDATES))


def extract_glyph(path: str) -> Image.Image:
    """Return the tight-cropped white 'io' glyph as RGBA (pure white + alpha).

    The decorative rings in the source are BLACK / low-alpha, so requiring a
    bright red channel plus meaningful alpha isolates the wordmark.
    """
    from PIL import ImageChops

    src = Image.open(path).convert("RGBA")
    r, _, _, a = src.split()

    bright = r.point(lambda v: 255 if v > 180 else 0)
    opaque = a.point(lambda v: 255 if v > 64 else 0)
    mask = ImageChops.multiply(bright, opaque)

    bbox = mask.getbbox()
    if bbox is None:
        sys.exit("Could not locate the logo glyph inside the source image.")

    glyph = Image.new("RGBA", (bbox[2] - bbox[0], bbox[3] - bbox[1]), (0, 0, 0, 0))
    glyph.paste(Image.new("RGBA", glyph.size, WHITE + (255,)), (0, 0))
    glyph.putalpha(mask.crop(bbox))
    return glyph


# ---------------------------------------------------------------------------
# Canvas helpers
# ---------------------------------------------------------------------------


def scaled_glyph(glyph: Image.Image, width: int) -> Image.Image:
    height = max(1, round(glyph.height * width / glyph.width))
    return glyph.resize((width, height), Image.LANCZOS)


def recolor(rgba: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    out = Image.new("RGBA", rgba.size, rgb + (0,))
    out.putalpha(rgba.getchannel("A"))
    return out


def _circle_mask(size: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    return m


def _rounded_mask(size: int, radius: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=radius, fill=255
    )
    return m


def place(canvas: Image.Image, glyph: Image.Image, colour, ratio, cy=0.5) -> None:
    inner = scaled_glyph(glyph, max(1, round(canvas.width * ratio)))
    inner = recolor(inner, colour)
    x = (canvas.width - inner.width) // 2
    y = round(canvas.height * cy - inner.height / 2)
    canvas.alpha_composite(inner, (x, y))


def make_icon(glyph: Image.Image, size: int, kind: str) -> Image.Image:
    """kind:
        'chip'       light disc  + dark glyph   <- favicon / model avatars
        'tile'       light tile  + dark glyph   <- maskable PWA icons
        'circle'     dark disc   + white glyph  <- dark-mode / swagger
        'square'     dark tile   + white glyph
        'white'      glyph only, white
        'black'      glyph only, dark
    """
    if kind in ("circle", "square", "chip", "tile"):
        dark = kind in ("circle", "square")
        mask = (
            _circle_mask(size)
            if kind in ("circle", "chip")
            else Image.new("L", (size, size), 255)
        )
        base = Image.new("RGBA", (size, size), (BRAND_DARK if dark else WHITE) + (0,))
        base.putalpha(mask)
        ratio = GLYPH_W_MASKABLE if kind == "tile" else GLYPH_W_TILE
        place(base, glyph, WHITE if dark else BRAND_DARK, ratio)
        return base

    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    place(
        base,
        glyph,
        WHITE if kind == "white" else BRAND_DARK,
        GLYPH_W_PLAIN,
    )
    return base


def save_png(img: Image.Image, directory: str, name: str) -> None:
    img.save(os.path.join(directory, name), "PNG", optimize=True)


def save_ico(img: Image.Image, directory: str, name: str = "favicon.ico") -> None:
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)]
    img.save(os.path.join(directory, name), format="ICO", sizes=sizes)


def save_svg(img: Image.Image, directory: str, name: str = "favicon.svg") -> None:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{img.width}" height="{img.height}" '
        f'viewBox="0 0 {img.width} {img.height}">\n'
        f'  <image width="{img.width}" height="{img.height}" '
        f'xlink:href="data:image/png;base64,{b64}"/>\n'
        "</svg>\n"
    )
    with open(os.path.join(directory, name), "w", encoding="utf-8") as fh:
        fh.write(svg)


# ---------------------------------------------------------------------------
# Manifest helpers (name / short_name changes live here)
# ---------------------------------------------------------------------------

APP_NAME = "Io-agent"
APP_SHORT_NAME = "Io-agent"


def patch_webmanifest(directory: str) -> None:
    path = os.path.join(directory, "site.webmanifest")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    raw = raw.replace('"name": "Open WebUI"', f'"name": "{APP_NAME}"')
    raw = raw.replace('"short_name": "WebUI"', f'"short_name": "{APP_SHORT_NAME}"')
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(raw)
    print(f"    patched  {os.path.relpath(path, REPO)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    source = find_source()
    print(f"Source logo : {source}")
    glyph = extract_glyph(source)
    print(f"Glyph bbox  : {glyph.size[0]}x{glyph.size[1]}  (aspect {glyph.width/glyph.height:.3f})")

    # Build the asset set once, then mirror it into every target directory.
    chip500 = make_icon(glyph, 500, "chip")    # white disc + dark glyph (the chip)
    dark500 = make_icon(glyph, 500, "circle")  # dark disc + white glyph
    dark_g500 = make_icon(glyph, 500, "black")   # glyph only, dark
    light_g500 = make_icon(glyph, 500, "white")  # glyph only, white
    chip96 = make_icon(glyph, 96, "chip")
    tile180 = make_icon(glyph, 180, "tile")
    tile192 = make_icon(glyph, 192, "tile")
    tile500 = make_icon(glyph, 500, "tile")
    tile512 = make_icon(glyph, 512, "tile")
    svg_src = make_icon(glyph, 512, "chip")

    assets: dict[str, Image.Image] = {
        "favicon.png": chip500,
        "favicon-dark.png": dark500,
        "favicon-96x96.png": chip96,
        "apple-touch-icon.png": tile180,
        "web-app-manifest-192x192.png": tile192,
        "web-app-manifest-512x512.png": tile512,
        "splash.png": dark_g500,
        "splash-dark.png": light_g500,
    }

    for directory in TARGET_DIRS:
        if not os.path.isdir(directory):
            sys.exit(f"Missing target directory: {directory}")
        print(f"\nWriting -> {os.path.relpath(directory, REPO)}")
        for name, img in assets.items():
            save_png(img, directory, name)
            print(f"    {name}")
        save_ico(chip500, directory)
        print("    favicon.ico")
        save_svg(svg_src, directory)
        print("    favicon.svg")
        patch_webmanifest(directory)

        # backend-only extras
        if directory == TARGET_DIRS[1]:
            # /static/logo.png is what the dynamic manifest handler publishes as
            # the installable PWA icon (declared "sizes": "500x500") -> full
            # -bleed light tile, which is maskable-safe.
            save_png(tile500, directory, "logo.png")
            print("    logo.png")
            swagger_dir = os.path.join(directory, "swagger-ui")
            if os.path.exists(os.path.join(swagger_dir, "favicon.png")):
                # Swagger's own page is white -> keep the dark chip there.
                save_png(dark500, swagger_dir, "favicon.png")
                print("    swagger-ui/favicon.png")

    # Repo-root static/ is Vite's publicDir, so it is what /favicon.png serves.
    # It sits outside TARGET_DIRS, hence the separate write - without it the
    # Arena model, Leaderboard and Arena model modal keep the upstream logo.
    root_public = os.path.join(REPO, "static")
    if os.path.isdir(os.path.join(root_public, "static")):
        save_png(chip500, root_public, "favicon.png")
        print(f"\nWriting -> {os.path.relpath(root_public, REPO)}")
        print("    favicon.png  (served at /favicon.png)")

    print("\nDone.")


if __name__ == "__main__":
    main()
