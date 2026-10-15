#!/usr/bin/env python3
"""Render contrib-heatmap.svg from data/contributions.json (real days only)."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
from pathlib import Path

from theme import BG, FONT, GREEN, HEATMAP, MUTED, PANEL, PANEL_EDGE, TITLEBAR

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "data" / "contributions.json"
DEFAULT_OUT = ROOT / "contrib-heatmap.svg"
WEEKDAYS = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
# GitHub calendar is Sunday-first; we still plot 7 rows Sun→Sat internally.


def load_data(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def weeks_from_days(days: list[dict]) -> list[list[dict | None]]:
    by_date = {d["date"]: d for d in days}
    start = dt.date.fromisoformat(days[0]["date"])
    end = dt.date.fromisoformat(days[-1]["date"])
    cursor = start - dt.timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    weeks: list[list[dict | None]] = []
    while cursor <= end:
        week: list[dict | None] = []
        for i in range(7):
            day = cursor + dt.timedelta(days=i)
            key = day.isoformat()
            week.append(by_date.get(key))
        weeks.append(week)
        cursor += dt.timedelta(days=7)
    if len(weeks) > 53:
        weeks = weeks[-53:]
    return weeks


def month_labels(weeks: list[list[dict | None]]) -> list[tuple[int, str]]:
    labels: list[tuple[int, str]] = []
    last_month = None
    months = "ene feb mar abr may jun jul ago sep oct nov dic".split()
    for i, week in enumerate(weeks):
        first = next((cell for cell in week if cell), None)
        if not first:
            continue
        month = dt.date.fromisoformat(first["date"]).month
        if month != last_month:
            labels.append((i, months[month - 1]))
            last_month = month
    return labels


def render(data: dict) -> str:
    days = data["days"]
    weeks = weeks_from_days(days)
    cell = 11
    gap = 3
    left = 44
    top = 92
    width = left + len(weeks) * (cell + gap) + 24
    height = top + 7 * (cell + gap) + 52
    total = data.get("total_contributions")
    total_txt = "—" if total is None else str(total)
    note = data.get("totals_note")
    stats = (
        f"{total_txt} contribuciones públicas  ·  "
        f"{data.get('active_days', 0)} días activos  ·  "
        f"racha {data.get('current_streak', {}).get('length', 0)}"
    )
    if note:
        stats += "  ·  total parcial"

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        'aria-label="Mapa de contribuciones de GitHub">',
        "<title>Contribuciones públicas de Enrique002</title>",
        f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>',
        f'<rect x="8" y="8" width="{width - 16}" height="{height - 16}" rx="8" '
        f'fill="{PANEL}" stroke="{PANEL_EDGE}"/>',
        f'<rect x="8" y="8" width="{width - 16}" height="36" rx="8" fill="{TITLEBAR}"/>',
        f'<rect x="8" y="34" width="{width - 16}" height="10" fill="{TITLEBAR}"/>',
        f'<text x="22" y="32" fill="{MUTED}" font-family="{FONT}" font-size="12">'
        "enrique@github ~ $ ./contributions.sh</text>",
        f'<text x="22" y="62" fill="{GREEN}" font-family="{FONT}" font-size="13">'
        f"{html.escape(stats)}</text>",
    ]

    for col, label in month_labels(weeks):
        x = left + col * (cell + gap)
        parts.append(
            f'<text x="{x}" y="{top - 8}" fill="{MUTED}" font-family="{FONT}" '
            f'font-size="10">{label}</text>'
        )

    # GitHub order: Sunday row 0.
    short = ("Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb")
    for row, name in enumerate(short):
        if row % 2 == 1:
            continue
        y = top + row * (cell + gap) + cell - 1
        parts.append(
            f'<text x="16" y="{y}" fill="{MUTED}" font-family="{FONT}" font-size="10">{name}</text>'
        )

    for col, week in enumerate(weeks):
        begin = f"{0.04 + col * 0.018:.3f}s"
        x = left + col * (cell + gap)
        parts.append(f'<g opacity="0">')
        for row, cell_data in enumerate(week):
            y = top + row * (cell + gap)
            if cell_data is None:
                fill = "#0f0f0f"
                title = ""
            else:
                fill = HEATMAP.get(int(cell_data.get("level") or 0), HEATMAP[0])
                count = cell_data.get("count")
                count_txt = "sin recuento" if count is None else f"{count} contrib."
                title = f"{cell_data['date']}: {count_txt}"
            title_xml = f"<title>{html.escape(title)}</title>" if title else ""
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}">{title_xml}</rect>'
            )
        parts.append(
            f'<animate attributeName="opacity" from="0" to="1" begin="{begin}" '
            f'dur="0.16s" fill="freeze"/></g>'
        )

    legend_y = top + 7 * (cell + gap) + 18
    parts.append(
        f'<text x="{left}" y="{legend_y}" fill="{MUTED}" font-family="{FONT}" '
        f'font-size="10">menos</text>'
    )
    lx = left + 42
    for level in range(5):
        parts.append(
            f'<rect x="{lx}" y="{legend_y - 10}" width="{cell}" height="{cell}" rx="2" '
            f'fill="{HEATMAP[level]}"/>'
        )
        lx += cell + gap
    parts.append(
        f'<text x="{lx + 4}" y="{legend_y}" fill="{MUTED}" font-family="{FONT}" '
        f'font-size="10">más</text>'
    )
    generated = html.escape(str(data.get("generated_at", "")))
    parts.append(
        f'<text x="{width - 20}" y="{legend_y}" text-anchor="end" fill="{MUTED}" '
        f'font-family="{FONT}" font-size="9">{generated}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Renderizar mapa de calor SVG.")
    parser.add_argument("--input", type=Path, default=DEFAULT_IN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if not args.input.is_file():
        raise SystemExit(f"No existe {args.input}. Ejecuta primero fetch_contributions.py")
    data = load_data(args.input)
    args.output.write_text(render(data), encoding="utf-8")
    print(f"SVG escrito: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
