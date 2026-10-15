#!/usr/bin/env python3
"""Convert a prepped grayscale image (or a local initials glyph) into an animated SVG."""

from __future__ import annotations

import argparse
import html
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from theme import BG, FONT, GREEN, MUTED

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "assets" / "prepped.png"
DEFAULT_OUT = ROOT / "enrique-ascii.svg"
RAMP = " .:-=+*#%@"


def _glyph_placeholder(cols: int, rows: int) -> Image.Image:
    """High-contrast initials, not a photograph."""
    img = Image.new("L", (cols * 10, rows * 16), 0)
    draw = ImageDraw.Draw(img)
    text = "E"
    try:
        font = ImageFont.truetype("arial.ttf", size=int(img.height * 0.72))
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (img.width - tw) // 2 - bbox[0]
    y = (img.height - th) // 2 - bbox[1] - int(img.height * 0.04)
    draw.text((x, y), text, fill=230, font=font)
    return img


def image_to_grid(image: Image.Image, cols: int, rows: int) -> list[str]:
    image = image.convert("RGBA")
    image = image.resize((cols, rows), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(image.convert("RGB"))
    gray = ImageOps.autocontrast(gray, cutoff=1)
    alpha = image.getchannel("A")
    pixels = list(gray.getdata())
    alphas = list(alpha.getdata())
    lines: list[str] = []
    n = len(RAMP) - 1
    for y in range(rows):
        chars: list[str] = []
        for x in range(cols):
            i = y * cols + x
            if alphas[i] < 28:
                chars.append(" ")
                continue
            lum = pixels[i] / 255.0
            if lum < 0.10:
                chars.append(" ")
                continue
            # Bias toward lighter glyphs so the portrait does not crush to black.
            lum = min(1.0, lum * 1.10 + 0.04)
            chars.append(RAMP[int(round(lum * n))])
        lines.append("".join(chars).rstrip())
    return lines


def lines_to_svg(lines: list[str], title: str) -> str:
    rows = len(lines)
    cols = max((len(line) for line in lines), default=1)
    char_w, char_h = 7.2, 11.2
    pad_x, pad_y = 18, 22
    width = int(pad_x * 2 + cols * char_w)
    height = int(pad_y * 2 + rows * char_h + 16)
    delay = 0.028
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="{html.escape(title)}">',
        f"<title>{html.escape(title)}</title>",
        f'<rect width="100%" height="100%" fill="{BG}"/>',
        f'<text x="{pad_x}" y="{pad_y - 6}" fill="{MUTED}" font-family="{FONT}" '
        f'font-size="10">enrique@github ~ $ python make_ascii_svg.py</text>',
        f'<g font-family="{FONT}" font-size="11" fill="{GREEN}" xml:space="preserve">',
    ]
    for i, line in enumerate(lines):
        y = pad_y + 10 + (i + 1) * char_h
        safe = html.escape(line) if line else " "
        begin = f"{i * delay:.3f}s"
        parts.append(
            f'<text x="{pad_x}" y="{y:.1f}" opacity="0">{safe}'
            f'<animate attributeName="opacity" from="0" to="1" begin="{begin}" '
            f'dur="0.12s" fill="freeze"/></text>'
        )
    parts.append("</g></svg>")
    return "\n".join(parts)


def build(src: Path | None, dest: Path, cols: int, rows: int, placeholder: bool) -> None:
    if placeholder or src is None or not src.is_file():
        print("Sin fotografía preparada: generando monograma ASCII (no es un retrato).")
        image = _glyph_placeholder(cols, rows)
        image = image.convert("RGBA")
    else:
        image = Image.open(src)
    grid = image_to_grid(image, cols, rows)
    dest.write_text(lines_to_svg(grid, "Retrato ASCII de Enrique002"), encoding="utf-8")
    print(f"SVG escrito: {dest} ({rows} filas)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generar retrato ASCII SVG.")
    parser.add_argument("--input", type=Path, default=DEFAULT_IN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cols", type=int, default=52)
    parser.add_argument("--rows", type=int, default=38)
    parser.add_argument(
        "--placeholder",
        action="store_true",
        help="Forzar monograma de iniciales si aún no hay fotografía.",
    )
    args = parser.parse_args()
    use_placeholder = args.placeholder or not args.input.is_file()
    build(args.input, args.output, args.cols, args.rows, use_placeholder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
