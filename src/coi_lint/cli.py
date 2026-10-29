"""coi-lint command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

from . import __version__
from .models import certificate_from_dict, requirements_from_dict
from .report import as_json, letter, text
from .rules import check, verdict


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="coi-lint", description="Lint certificates of insurance against your requirements.")
    ap.add_argument("--version", action="version", version=f"coi-lint {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ck = sub.add_parser("check", help="check one normalised certificate (JSON) against a requirements file (YAML)")
    ck.add_argument("certificate", type=Path)
    ck.add_argument("--rules", type=Path, required=True)
    ck.add_argument("--format", choices=["text", "json", "letter"], default="text")
    ck.add_argument("--today", help="override today's date (YYYY-MM-DD), for reproducible runs")
    ck.add_argument("--no-color", action="store_true")
    a = ap.parse_args(argv)

    try:
        cert = certificate_from_dict(json.loads(a.certificate.read_text()), source=str(a.certificate))
        req = requirements_from_dict(yaml.safe_load(a.rules.read_text()))
        today = date.fromisoformat(a.today) if a.today else None
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"coi-lint: {exc}", file=sys.stderr)
        return 2

    findings = check(cert, req, today)
    if a.format == "json":
        print(as_json(cert, req, findings))
    elif a.format == "letter":
        print(letter(cert, req, findings))
    else:
        print(text(cert, req, findings, color=not a.no_color and sys.stdout.isatty()))
    return 1 if verdict(findings) == "DEFICIENT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
