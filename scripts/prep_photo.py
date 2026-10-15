#!/usr/bin/env python3
"""Prepare a local photograph for ASCII conversion.

Does not upload or copy the original into the public tree. Writes a
high-contrast grayscale PNG to assets/prepped.png (gitignored).

Background removal uses rembg when installed; otherwise a luminance
threshold is applied so dark or uniform backdrops drop out.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "assets" / "prepped.png"


def _try_rembg(image: Image.Image) -> Image.Image:
    try:
        from rembg import remove  # type: ignore
    except ImportError:
        print("rembg no está instalado; se usará un recorte por luminancia.", file=sys.stderr)
        return image

    print("Eliminando fondo con rembg…")
    rgba = image.convert("RGBA")
    return remove(rgba)


def _luma_mask(image: Image.Image) -> Image.Image:
    """Drop near-uniform / very light or very dark backdrops when rembg is absent."""
    rgba = image.convert("RGBA")
    gray = ImageOps.grayscale(rgba)
    extrema = gray.getextrema()
    if extrema[1] - extrema[0] < 8:
        return rgba

    edges = gray.filter(ImageFilter.FIND_EDGES)
    # Keep pixels that are either high-detail or mid-tone (likely the subject).
    out = Image.new("RGBA", rgba.size)
    src = rgba.load()
    g = gray.load()
    e = edges.load()
    dst = out.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, gch, b, a = src[x, y]
            lum = g[x, y]
            edge = e[x, y]
            # Corners that are very light or very dark and low-edge → transparent.
            near_border = x < w * 0.04 or x > w * 0.96 or y < h * 0.04 or y > h * 0.96
            if near_border and edge < 12 and (lum > 220 or lum < 18):
                dst[x, y] = (r, gch, b, 0)
            else:
                dst[x, y] = (r, gch, b, a)
    return out


def prepare(src: Path, dest: Path, size: int = 720) -> Path:
    image = Image.open(src)
    image = ImageOps.exif_transpose(image)
    image.thumbnail((size, size), Image.Resampling.LANCZOS)

    image = _try_rembg(image)
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    else:
        # rembg already produced alpha; still tighten obvious leftover backdrop.
        pass

    if image.getextrema()[-1][1] == 255 and image.getextrema()[-1][0] == 255:
        image = _luma_mask(image)

    gray = ImageOps.grayscale(image.convert("RGB"))
    gray = ImageOps.autocontrast(gray, cutoff=2)
    gray = ImageEnhance.Contrast(gray).enhance(1.35)
    gray = ImageEnhance.Brightness(gray).enhance(1.12)

    rgba = Image.new("RGBA", gray.size)
    alpha = image.getchannel("A") if "A" in image.getbands() else Image.new("L", gray.size, 255)
    rgba.paste(gray.convert("RGBA"))
    rgba.putalpha(alpha)

    dest.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(dest, "PNG")
    print(f"Imagen preparada: {dest}")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Preparar fotografía para retrato ASCII.")
    parser.add_argument("photo", type=Path, help="Ruta local a la fotografía (no se sube al repo).")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--size", type=int, default=720)
    args = parser.parse_args()
    if not args.photo.is_file():
        print(f"No encuentro la fotografía: {args.photo}", file=sys.stderr)
        return 2
    prepare(args.photo, args.output, size=args.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
