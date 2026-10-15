#!/usr/bin/env python3
"""Render a Neofetch-style SVG info card from data/info.json."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from theme import (
    BG,
    DIM,
    DOT_GREEN,
    DOT_RED,
    DOT_YELLOW,
    FG,
    FONT,
    GREEN,
    MUTED,
    PANEL,
    PANEL_EDGE,
    TITLEBAR,
)

ROOT = Path(__file__).resolve().parent.parent
INFO_PATH = ROOT / "data" / "info.json"
DEFAULT_OUT = ROOT / "info-card.svg"


def load_info(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rows_from_info(info: dict) -> list[tuple[str, str]]:
    featured = info.get("featured_project") or {}
    featured_value = featured.get("name", "")
    if featured.get("note"):
        featured_value = f"{featured_value}  ·  {featured['note']}"
    stack = ", ".join(info.get("stack_projects") or [])
    also = ", ".join(info.get("stack_also") or [])
    other = ", ".join(info.get("other") or [])
    interests = ", ".join(info.get("interests") or [])
    rows = [
        ("Usuario", info.get("user", "")),
        ("Nombre", info.get("name", "")),
        ("Perfil", info.get("title", "")),
        ("Host", info.get("host", "github.com")),
        ("Formación", info.get("education", "")),
        ("Proyecto", featured_value),
        ("Stack", stack),
        ("También", also + " (no aparece aún en repos públicos)"),
        ("Otros", other),
        ("Intereses", interests),
        ("GitHub", (info.get("github") or "").replace("https://", "").replace("http://", "")),
    ]
    return [(k, v) for k, v in rows if v]


def render(info: dict) -> str:
    rows = rows_from_info(info)
    label_w = max(len(k) for k, _ in rows)
    line_h = 22
    pad_x = 22
    width = 740
    header_h = 42
    body_top = 70
    height = body_top + 28 + line_h * (len(rows) + 2)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        'aria-label="Tarjeta de información de Enrique002">',
        "<title>enrique@github — neofetch</title>",
        f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>',
        f'<rect x="8" y="8" width="{width - 16}" height="{height - 16}" rx="8" '
        f'fill="{PANEL}" stroke="{PANEL_EDGE}" stroke-width="1"/>',
        f'<rect x="8" y="8" width="{width - 16}" height="{header_h}" rx="8" fill="{TITLEBAR}"/>',
        f'<rect x="8" y="{8 + header_h - 10}" width="{width - 16}" height="10" fill="{TITLEBAR}"/>',
        f'<circle cx="28" cy="28" r="5" fill="{DOT_RED}"/>',
        f'<circle cx="46" cy="28" r="5" fill="{DOT_YELLOW}"/>',
        f'<circle cx="64" cy="28" r="5" fill="{DOT_GREEN}"/>',
        f'<text x="{width / 2:.0f}" y="33" text-anchor="middle" fill="{MUTED}" '
        f'font-family="{FONT}" font-size="12">enrique@github — zsh — neofetch</text>',
        f'<g font-family="{FONT}" font-size="13">',
        f'<text x="{pad_x}" y="{body_top}" fill="{GREEN}">$ neofetch --user Enrique002</text>',
    ]

    for i, (key, value) in enumerate(rows):
        y = body_top + 28 + i * line_h
        begin = f"{0.18 + i * 0.09:.2f}s"
        label = html.escape(key.ljust(label_w))
        val = html.escape(value)
        parts.append(
            f'<g opacity="0">'
            f'<text x="{pad_x}" y="{y}" xml:space="preserve">'
            f'<tspan fill="{GREEN}">{label}</tspan>'
            f'<tspan fill="{DIM}"> : </tspan>'
            f'<tspan fill="{FG}">{val}</tspan></text>'
            f'<animate attributeName="opacity" from="0" to="1" begin="{begin}" '
            f'dur="0.18s" fill="freeze"/></g>'
        )

    end_y = body_top + 28 + len(rows) * line_h + 8
    parts.append(
        f'<text x="{pad_x}" y="{end_y}" fill="{GREEN}" opacity="0">█'
        f'<animate attributeName="opacity" values="0;1;0" begin="{0.18 + len(rows) * 0.09:.2f}s" '
        f'dur="1.1s" repeatCount="2" fill="freeze"/></text>'
    )
    parts.append("</g></svg>")
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generar tarjeta Neofetch SVG.")
    parser.add_argument("--info", type=Path, default=INFO_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    info = load_info(args.info)
    args.output.write_text(render(info), encoding="utf-8")
    print(f"SVG escrito: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
