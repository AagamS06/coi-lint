"""coi-lint command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

from . import __version__, export
from .models import certificate_from_dict, requirements_from_dict
from .renewals import collect, due, load_certificates
from .report import as_json, letter, renewals_text, text
from .rules import check, verdict


def _today(value: str | None) -> date:
    return date.fromisoformat(value) if value else date.today()  # noqa: DTZ011 (local calendar date is intended)


def _check(a: argparse.Namespace) -> int:
    try:
        cert = certificate_from_dict(json.loads(a.certificate.read_text()), source=str(a.certificate))
        req = requirements_from_dict(yaml.safe_load(a.rules.read_text()))
        today = _today(a.today)
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


def _renewals(a: argparse.Namespace) -> int:
    try:
        today = _today(a.today)
        certs = load_certificates(a.paths)
        kinds = None
        if a.rules:
            req = requirements_from_dict(yaml.safe_load(a.rules.read_text()))
            kinds = {c.kind for c in req.coverages}
        if a.within < 0:
            raise ValueError("--within must be 0 or more days")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"coi-lint: {exc}", file=sys.stderr)
        return 2

    everything = collect(certs, today, kinds)
    shown = due(everything, a.within)
    if a.ics:
        try:
            a.ics.write_text(export.ics(everything, today), newline="")
        except OSError as exc:
            print(f"coi-lint: {exc}", file=sys.stderr)
            return 2
    if a.format == "json":
        print(export.as_json(shown, today, a.within))
    elif a.format == "letter":
        print(export.letters(shown))
    else:
        print(renewals_text(shown, len(certs), today, a.within, color=not a.no_color and sys.stdout.isatty()))
        if a.ics:
            n = sum(r.days_left >= 0 for r in everything)
            print(f"\nCalendar: {n} upcoming expiries written to {a.ics} (reminders 90, 60 and 30 days before)")
    return 1 if any(r.days_left < 0 for r in shown) else 0


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
    ck.set_defaults(func=_check)

    rn = sub.add_parser("renewals", help="list policies expiring soon across many certificates; export a calendar")
    rn.add_argument("paths", type=Path, nargs="+", help="certificate JSON files and/or folders of them")
    rn.add_argument("--within", type=int, default=90, help="show policies expiring within this many days (default 90)")
    rn.add_argument("--rules", type=Path, help="only track the coverages this requirements file asks for")
    rn.add_argument("--ics", type=Path, help="write every upcoming expiry to this .ics calendar file")
    rn.add_argument("--format", choices=["text", "json", "letter"], default="text")
    rn.add_argument("--today", help="override today's date (YYYY-MM-DD), for reproducible runs")
    rn.add_argument("--no-color", action="store_true")
    rn.set_defaults(func=_renewals)

    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
