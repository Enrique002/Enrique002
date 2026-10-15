#!/usr/bin/env python3
"""Validate generated artifacts: SVG XML, JSON shape, README paths, workflow, offline fetch."""

from __future__ import annotations

import json
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import fetch_contributions as fc  # noqa: E402

SVG_FILES = [
    ROOT / "enrique-ascii.svg",
    ROOT / "info-card.svg",
    ROOT / "contrib-heatmap.svg",
]
README = ROOT / "README.md"
WORKFLOW = ROOT / ".github" / "workflows" / "update-profile-art.yml"
JSON_PATH = ROOT / "data" / "contributions.json"


class Failures(list):
    def check(self, cond: bool, msg: str) -> None:
        if not cond:
            self.append(msg)


def validate_svg(path: Path, failures: Failures) -> None:
    if not path.is_file():
        failures.append(f"Falta {path.name}")
        return
    text = path.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        failures.append(f"XML inválido en {path.name}: {exc}")
        return
    tag = root.tag.split("}")[-1]
    failures.check(tag == "svg", f"{path.name} raíz no es <svg>")
    failures.check("<script" not in text.lower(), f"{path.name} contiene script")
    stripped = (
        text.replace("http://www.w3.org/2000/svg", "")
        .replace("http://www.w3.org/1999/xlink", "")
    )
    failures.check(
        "http://" not in stripped and "https://" not in stripped,
        f"{path.name} referencia URLs externas inesperadas",
    )


def validate_json(failures: Failures) -> None:
    if not JSON_PATH.is_file():
        failures.append("Falta data/contributions.json")
        return
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    for key in ("username", "generated_at", "range", "days"):
        failures.check(key in data, f"JSON sin clave {key}")
    days = data.get("days") or []
    failures.check(len(days) >= 7, "JSON con menos de 7 días")
    dates = []
    for day in days:
        failures.check("date" in day and "level" in day, f"día mal formado: {day}")
        dates.append(day["date"])
        failures.check(0 <= int(day["level"]) <= 4, f"level fuera de rango: {day}")
    failures.check(dates == sorted(dates), "días no ordenados")
    failures.check(len(dates) == len(set(dates)), "fechas duplicadas")


def validate_readme(failures: Failures) -> None:
    text = README.read_text(encoding="utf-8")
    for name in ("enrique-ascii.svg", "info-card.svg", "contrib-heatmap.svg"):
        failures.check(name in text, f"README no referencia {name}")
        failures.check((ROOT / name).is_file(), f"README apunta a {name} inexistente")
    failures.check("shields.io" not in text, "README usa shields.io (terceros)")
    failures.check("github-readme-stats" not in text, "README usa stats de terceros")


def validate_workflow(failures: Failures) -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    failures.check("workflow_dispatch" in text, "workflow sin ejecución manual")
    failures.check("schedule" in text, "workflow sin cron diario")
    failures.check("contents: write" in text, "workflow sin contents: write")
    failures.check("requirements-heatmap.txt" in text, "workflow no usa deps mínimas del heatmap")
    failures.check("fetch_contributions.py" in text, "workflow no obtiene contribuciones")
    failures.check("render_heatmap_svg.py" in text, "workflow no renderiza el SVG")
    failures.check("[skip ci]" in text or "skip ci" in text, "commits automáticos sin skip ci")


def validate_offline_keeps_json(failures: Failures) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "contributions.json"
        original = {"username": "Enrique002", "days": [{"date": "2026-01-01", "count": 1, "level": 1}]}
        tmp_path.write_text(json.dumps(original), encoding="utf-8")

        def boom(*_a, **_k):
            raise fc.FetchError("Sin conexión (prueba)")

        argv = ["fetch_contributions.py", "--output", str(tmp_path), "--user", "Enrique002"]
        with mock.patch.object(fc, "fetch_html", boom):
            with mock.patch.object(sys, "argv", argv):
                code = fc.main()
        failures.check(code == 1, f"offline debía salir 1, salió {code}")
        kept = json.loads(tmp_path.read_text(encoding="utf-8"))
        failures.check(kept == original, "el JSON previo se sobrescribió en el fallo de red")


def validate_bad_html(failures: Failures) -> None:
    try:
        fc.parse_days("<html><body>sin calendario</body></html>")
        failures.append("HTML vacío no levantó FetchError")
    except fc.FetchError:
        pass


def validate_fixture_html(failures: Failures) -> None:
    fixture = SCRIPTS / "fixtures" / "calendar_snippet.html"
    days = fc.parse_days(fixture.read_text(encoding="utf-8"))
    failures.check(len(days) == 7, f"fixture debía tener 7 días, tiene {len(days)}")
    payload = fc.build_payload("Enrique002", days)
    failures.check(payload["total_contributions"] == 26, "suma del fixture incorrecta")
    failures.check(payload["best_day"]["count"] == 12, "mejor día del fixture incorrecto")


def main() -> int:
    failures = Failures()
    for svg in SVG_FILES:
        validate_svg(svg, failures)
    validate_json(failures)
    validate_readme(failures)
    validate_workflow(failures)
    validate_offline_keeps_json(failures)
    validate_bad_html(failures)
    validate_fixture_html(failures)
    if failures:
        print("VALIDACIÓN FALLIDA:")
        for item in failures:
            print(f" - {item}")
        return 1
    print("Validación OK: SVG, JSON, README, workflow y fallo de red.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
