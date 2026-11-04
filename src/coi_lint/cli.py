"""coi-lint command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

from . import __version__, export, project
from .config import load_requirements
from .extract import extract, load_documents, load_fieldmap
from .inbox import certificate_findings
from .inbox import run as run_inbox
from .notify import post_slack, webhook_from_env
from .renewals import collect, due, load_certificates
from .report import as_json, letter, renewals_text, text
from .rules import RULES, explain, verdict
from .waivers import load_waivers, stats

USER_ERRORS = (OSError, ValueError, KeyError, yaml.YAMLError, json.JSONDecodeError)


def _today(value: str | None) -> date:
    return date.fromisoformat(value) if value else date.today()  # noqa: DTZ011 (local calendar date is intended)


def _color(a: argparse.Namespace) -> bool:
    return not a.no_color and sys.stdout.isatty()


def _err(exc: Exception) -> int:
    print(f"coi-lint: {exc}", file=sys.stderr)
    return 2


def _check(a: argparse.Namespace) -> int:
    try:
        today = _today(a.today)
        waivers = load_waivers(a.waivers) if a.waivers else []
        fm = load_fieldmap(a.fieldmap) if a.certificate.suffix.lower() == ".pdf" else None
        data = extract(a.certificate, fm) if fm else json.loads(a.certificate.read_text())
        data.setdefault("source", str(a.certificate))
        cert, req, findings = certificate_findings(data, a.rules, waivers, today, a.pack)
    except USER_ERRORS as exc:
        return _err(exc)
    if a.format == "json":
        print(as_json(cert, req, findings))
    elif a.format == "letter":
        print(letter(cert, req, findings))
    else:
        print(text(cert, req, findings, color=_color(a), fixes=not a.no_fixes))
    return 1 if verdict(findings) == "DEFICIENT" else 0


def _extract(a: argparse.Namespace) -> int:
    try:
        data = extract(a.pdf, load_fieldmap(a.fieldmap))
    except USER_ERRORS as exc:
        return _err(exc)
    print(json.dumps(data, indent=2))
    return 1 if data["_unreadable"] else 0


def _explain(a: argparse.Namespace) -> int:
    try:
        if a.rules:
            load_requirements(a.rules)        # registers the file's pack rules
        if a.rule is None:
            for rid in sorted(RULES):
                print(f"{rid}  {RULES[rid]['title']}")
            return 0
        print(explain(a.rule))
    except USER_ERRORS as exc:
        return _err(exc)
    return 0


def _slack(a: argparse.Namespace, message: str) -> int | None:
    if not getattr(a, "slack_env", None):
        return None
    try:
        post_slack(webhook_from_env(a.slack_env), message)
    except USER_ERRORS as exc:
        return _err(exc)
    return None


def _renewals(a: argparse.Namespace) -> int:
    try:
        today = _today(a.today)
        certs = load_certificates(a.paths)
        kinds = None
        if a.rules:
            req, _ = load_requirements(a.rules)
            kinds = {c.kind for c in req.coverages}
        if a.within < 0:
            raise ValueError("--within must be 0 or more days")
    except USER_ERRORS as exc:
        return _err(exc)

    everything = collect(certs, today, kinds)
    shown = due(everything, a.within)
    if a.ics:
        try:
            a.ics.write_text(export.ics(everything, today), newline="")
        except OSError as exc:
            return _err(exc)
    if a.format == "json":
        print(export.as_json(shown, today, a.within))
    elif a.format == "letter":
        print(export.letters(shown))
    else:
        print(renewals_text(shown, len(certs), today, a.within, color=_color(a)))
        if a.ics:
            n = sum(r.days_left >= 0 for r in everything)
            print(f"\nCalendar: {n} upcoming expiries written to {a.ics} (reminders 90, 60 and 30 days before)")
    expired = sum(r.days_left < 0 for r in shown)
    rc = _slack(a, f"coi-lint renewals: {len(shown)} due in the next {a.within} days"
                   + (f", {expired} already expired" if expired else "") + ".")
    if rc is not None:
        return rc
    return 1 if expired else 0


def _report(a: argparse.Namespace) -> int:
    try:
        today = _today(a.today)
        waivers = load_waivers(a.waivers) if a.waivers else []
        rows = []
        for d in load_documents(a.paths, load_fieldmap(a.fieldmap)):
            cert, req, findings = certificate_findings(d, a.rules, waivers, today, a.pack)
            rows.append(project.Row(cert, findings))
        renewals = due(collect([r.cert for r in rows], today), a.within)
        s = project.summary(rows, renewals, a.name or req.name, today)
    except USER_ERRORS as exc:
        return _err(exc)
    out = {"md": project.markdown, "html": project.to_html, "csv": project.to_csv, "json": project.to_json}[a.format](s)
    if a.out:
        try:
            a.out.write_text(out)
        except OSError as exc:
            return _err(exc)
        print(f"{project.headline(s)}\nReport written to {a.out}")
    else:
        print(out, end="")
    rc = _slack(a, project.headline(s))
    if rc is not None:
        return rc
    return 1 if s["deficient"] else 0


def _waivers(a: argparse.Namespace) -> int:
    try:
        print(stats(load_waivers(a.file), _today(a.today)))
    except USER_ERRORS as exc:
        return _err(exc)
    return 0


def _watch(a: argparse.Namespace) -> int:
    try:
        waivers = load_waivers(a.waivers) if a.waivers else []
        load_requirements(a.rules)        # fail fast on a bad requirements file
        run_inbox(a.host, a.user, a.password_env, a.folder, a.drafts, a.rules, waivers, a.state, a.fieldmap,
                  a.once, a.interval)
    except USER_ERRORS as exc:
        return _err(exc)
    except KeyboardInterrupt:
        return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="coi-lint", description="Lint certificates of insurance against your requirements.")
    ap.add_argument("--version", action="version", version=f"coi-lint {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p: argparse.ArgumentParser, color: bool = True) -> None:
        p.add_argument("--today", help="override today's date (YYYY-MM-DD), for reproducible runs")
        if color:
            p.add_argument("--no-color", action="store_true")

    ck = sub.add_parser("check", help="check one certificate (JSON or PDF) against a requirements file (YAML)")
    ck.add_argument("certificate", type=Path)
    ck.add_argument("--rules", type=Path, required=True)
    ck.add_argument("--pack", type=Path, action="append", default=[], help="extra rule pack (YAML); repeatable")
    ck.add_argument("--waivers", type=Path, help="waivers file (YAML)")
    ck.add_argument("--fieldmap", type=Path, help="field map for PDF input (default: the bundled sample map)")
    ck.add_argument("--format", choices=["text", "json", "letter"], default="text")
    ck.add_argument("--no-fixes", action="store_true", help="hide the fix suggestion under each problem")
    common(ck)
    ck.set_defaults(func=_check)

    ex = sub.add_parser("extract", help="read a certificate PDF into JSON (form fields, text, or OCR)")
    ex.add_argument("pdf", type=Path)
    ex.add_argument("--fieldmap", type=Path)
    ex.set_defaults(func=_extract)

    xp = sub.add_parser("explain", help="explain a rule id (or list all rules)")
    xp.add_argument("rule", nargs="?")
    xp.add_argument("--rules", type=Path, help="also load rule packs referenced by this requirements file")
    xp.set_defaults(func=_explain)

    rn = sub.add_parser("renewals", help="list policies expiring soon across many certificates; export a calendar")
    rn.add_argument("paths", type=Path, nargs="+", help="certificate JSON/PDF files and/or folders of them")
    rn.add_argument("--within", type=int, default=90, help="show policies expiring within this many days (default 90)")
    rn.add_argument("--rules", type=Path, help="only track the coverages this requirements file asks for")
    rn.add_argument("--ics", type=Path, help="write every upcoming expiry to this .ics calendar file")
    rn.add_argument("--format", choices=["text", "json", "letter"], default="text")
    rn.add_argument("--slack-env", help="name of an env var holding a Slack webhook URL to post a summary to")
    common(rn)
    rn.set_defaults(func=_renewals)

    rp = sub.add_parser("report", help="compliance report for a whole project (Markdown, HTML, CSV or JSON)")
    rp.add_argument("paths", type=Path, nargs="+", help="certificate JSON/PDF files and/or folders of them")
    rp.add_argument("--rules", type=Path, required=True)
    rp.add_argument("--pack", type=Path, action="append", default=[])
    rp.add_argument("--waivers", type=Path)
    rp.add_argument("--fieldmap", type=Path)
    rp.add_argument("--name", help="project name for the heading (default: the requirements name)")
    rp.add_argument("--within", type=int, default=90, help="renewals window in days (default 90)")
    rp.add_argument("--format", choices=["md", "html", "csv", "json"], default="md")
    rp.add_argument("--out", type=Path, help="write the report to this file instead of stdout")
    rp.add_argument("--slack-env", help="name of an env var holding a Slack webhook URL to post the headline to")
    common(rp, color=False)
    rp.set_defaults(func=_report)

    wv = sub.add_parser("waivers", help="summarise a waivers file: which rules get waived most")
    wv.add_argument("file", type=Path)
    common(wv, color=False)
    wv.set_defaults(func=_waivers)

    wi = sub.add_parser("watch-inbox", help="check certificates arriving by email and save draft replies (never sends)")
    wi.add_argument("--host", required=True, help="IMAP host, e.g. imap.gmail.com")
    wi.add_argument("--user", required=True, help="mailbox address")
    wi.add_argument("--password-env", required=True, help="name of the env var holding an app password")
    wi.add_argument("--rules", type=Path, required=True)
    wi.add_argument("--waivers", type=Path)
    wi.add_argument("--fieldmap", type=Path)
    wi.add_argument("--folder", default="INBOX", help="folder to read (default INBOX; a dedicated label is safer)")
    wi.add_argument("--drafts", default="Drafts", help='drafts folder (Gmail: "[Gmail]/Drafts")')
    wi.add_argument("--state", type=Path, default=Path(".coi-lint-inbox.json"), help="remembers handled emails")
    wi.add_argument("--once", action="store_true", help="one pass, then exit (for cron / Task Scheduler)")
    wi.add_argument("--interval", type=int, default=300, help="seconds between passes (minimum 60)")
    wi.set_defaults(func=_watch)

    a = ap.parse_args(argv)
    return a.func(a)


PRECOMMIT_FLAGS = {"--no-color", "--no-fixes"}


def precommit_main(argv: list[str] | None = None) -> int:
    """pre-commit hook: options first, then the changed certificate files; check each file."""
    args = sys.argv[1:] if argv is None else list(argv)
    opts: list[str] = []
    files: list[str] = []
    i = 0
    while i < len(args):
        if args[i].startswith("--"):
            takes_value = args[i] not in PRECOMMIT_FLAGS and "=" not in args[i] and i + 1 < len(args)
            opts.extend(args[i:i + 2] if takes_value else args[i:i + 1])
            i += 2 if takes_value else 1
        else:
            files.append(args[i])
            i += 1
    rc = 0
    for f in files:
        rc = max(rc, main(["check", f, *opts, "--no-color"]))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
