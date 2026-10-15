#!/usr/bin/env python3
"""Fetch public GitHub contribution days for a user without a personal token.

Source: https://github.com/users/<login>/contributions

On network or markup failures the previous data/contributions.json is kept.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "contributions.json"
USERNAME = os.environ.get("GH_PROFILE_USER", "Enrique002")
ENDPOINT = "https://github.com/users/{user}/contributions"
UA = "Enrique002-profile-heatmap/1.0 (+https://github.com/Enrique002/Enrique002)"


class FetchError(Exception):
    pass


def fetch_html(user: str, timeout: int = 30) -> str:
    url = ENDPOINT.format(user=user)
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} al pedir {url}") from exc
    except URLError as exc:
        raise FetchError(f"Sin conexión o DNS al pedir {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise FetchError(f"Tiempo agotado al pedir {url}") from exc


def _count_from_label(text: str) -> int | None:
    if not text:
        return None
    if re.search(r"no contributions", text, re.I):
        return 0
    match = re.search(r"(\d+)\s+contribution", text, re.I)
    if match:
        return int(match.group(1))
    match = re.match(r"(\d+)", text.strip())
    return int(match.group(1)) if match else None


def parse_days(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        cells = soup.select("rect.ContributionCalendar-day")
    if not cells:
        raise FetchError(
            "No hay celdas del calendario. GitHub pudo cambiar el HTML público. "
            "Alternativa: definir GH_CONTRIBUTIONS_HTML con una captura local."
        )

    days: list[dict] = []
    for cell in cells:
        date = cell.get("data-date")
        if not date:
            continue
        try:
            dt.date.fromisoformat(date)
        except ValueError:
            continue
        level_raw = cell.get("data-level") or "0"
        try:
            level = int(level_raw)
        except ValueError:
            level = 0
        tooltip = None
        cell_id = cell.get("id")
        if cell_id:
            tip = soup.find("tool-tip", attrs={"for": cell_id})
            if tip:
                tooltip = tip.get_text(" ", strip=True)
        label = tooltip or cell.get("aria-label") or ""
        count = _count_from_label(label)
        if count is None:
            count = 0 if level == 0 else None
        days.append({"date": date, "count": count, "level": max(0, min(level, 4))})

    days.sort(key=lambda d: d["date"])
    # Deduplicate by date if GitHub echoed extra cells.
    unique: dict[str, dict] = {}
    for day in days:
        unique[day["date"]] = day
    days = [unique[k] for k in sorted(unique)]
    if len(days) < 7:
        raise FetchError(f"Calendario incompleto: solo {len(days)} días.")
    return days


def _consecutive(days: list[dict], *, current: bool) -> tuple[int, str | None, str | None]:
    def active(entry: dict) -> bool:
        if entry["count"] is not None:
            return entry["count"] > 0
        return entry["level"] > 0

    if current:
        idx = len(days) - 1
        if not active(days[idx]) and idx > 0:
            idx -= 1
        end_idx = idx
        length = 0
        while idx >= 0 and active(days[idx]):
            length += 1
            idx -= 1
        if length == 0:
            return 0, None, None
        return length, days[idx + 1]["date"], days[end_idx]["date"]

    best = run = 0
    best_start = best_end = run_start = None
    for entry in days:
        if active(entry):
            if run == 0:
                run_start = entry["date"]
            run += 1
            if run > best:
                best, best_start, best_end = run, run_start, entry["date"]
        else:
            run = 0
    return best, best_start, best_end


def build_payload(user: str, days: list[dict]) -> dict:
    numbered = [d["count"] for d in days if isinstance(d["count"], int)]
    total = sum(numbered) if numbered else None
    if total is not None and any(d["count"] is None for d in days):
        totals_note = "total_incomplete_missing_tooltips"
    else:
        totals_note = None
    active_days = sum(
        1
        for d in days
        if (d["count"] or 0) > 0 or (d["count"] is None and d["level"] > 0)
    )
    best = max(days, key=lambda d: (d["count"] if d["count"] is not None else d["level"], d["date"]))
    cur_len, cur_start, cur_end = _consecutive(days, current=True)
    long_len, long_start, long_end = _consecutive(days, current=False)
    return {
        "username": user,
        "source": ENDPOINT.format(user=user),
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "total_contributions": total,
        "totals_note": totals_note,
        "active_days": active_days,
        "current_streak": {"length": cur_len, "start": cur_start, "end": cur_end},
        "longest_streak": {"length": long_len, "start": long_start, "end": long_end},
        "best_day": {"date": best["date"], "count": best["count"], "level": best["level"]},
        "days": days,
    }


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="contrib-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Obtener contribuciones públicas de GitHub.")
    parser.add_argument("--user", default=USERNAME)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--html-file", type=Path, help="Parsear un HTML local (pruebas / fallback).")
    args = parser.parse_args()
    previous = args.output if args.output.is_file() else None
    try:
        if args.html_file:
            html = args.html_file.read_text(encoding="utf-8")
        else:
            html = fetch_html(args.user)
        days = parse_days(html)
        payload = build_payload(args.user, days)
        atomic_write(args.output, payload)
        print(
            f"OK {args.output}: {len(days)} días, "
            f"total={payload['total_contributions']}, "
            f"racha={payload['current_streak']['length']}"
        )
        return 0
    except FetchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if previous:
            backup = args.output.with_suffix(".json.last-good")
            shutil.copy2(previous, backup)
            print(f"Se conserva el último JSON válido: {previous}", file=sys.stderr)
        else:
            print("No había un JSON previo que conservar.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
