"""Waivers: the "learnings" layer. Record a decision once and coi-lint remembers it.

waivers.yaml:

    waivers:
      - insured: Northside Electric        # substring match, case-insensitive
        rule: COI007                       # rule id (built-in or pack)
        coverage: general_liability        # optional: only this coverage
        reason: Waiver of subrogation not required for this trade per contract clause 14.3
        approved_by: J. Example
        until: 2027-03-01                  # required: waivers must expire

A matching fail/warn finding becomes "waived" (it no longer affects the verdict) and keeps the
reason. Expired waivers stop applying and are reported so they get reviewed, never silently kept.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

import yaml

from .rules import Finding


@dataclass
class Waiver:
    insured: str
    rule: str
    reason: str
    until: date
    approved_by: str = ""
    coverage: str | None = None


def load_waivers(path: Path) -> list[Waiver]:
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"waivers file {path}: {exc}") from exc
    out = []
    for i, w in enumerate(data.get("waivers", []), 1):
        where = f"waivers file {path} entry #{i}"
        for k in ("insured", "rule", "reason", "until"):
            if not w.get(k):
                raise ValueError(f"{where}: '{k}' is required")
        try:
            until = w["until"] if isinstance(w["until"], date) else date.fromisoformat(str(w["until"]))
        except ValueError as exc:
            raise ValueError(f"{where}: bad 'until' date: {exc}") from exc
        out.append(Waiver(str(w["insured"]), str(w["rule"]).upper(), str(w["reason"]), until,
                          str(w.get("approved_by", "")), w.get("coverage")))
    return out


def _matches(w: Waiver, f: Finding, insured: str) -> bool:
    return (w.insured.lower() in insured.lower() and w.rule == f.rule
            and (w.coverage is None or w.coverage == f.coverage))


def apply(findings: list[Finding], insured: str, waivers: list[Waiver], today: date) -> list[Finding]:
    out = []
    for f in findings:
        if f.severity not in ("fail", "warn"):
            out.append(f)
            continue
        active = [w for w in waivers if _matches(w, f, insured) and w.until >= today]
        expired = [w for w in waivers if _matches(w, f, insured) and w.until < today]
        if active:
            w = active[0]
            who = f", approved by {w.approved_by}" if w.approved_by else ""
            out.append(replace(f, severity="waived", waiver=f"{w.reason} (until {w.until.isoformat()}{who})"))
        elif expired:
            note = f" [waiver expired {max(w.until for w in expired).isoformat()}: review it]"
            out.append(replace(f, message=f.message + note))
        else:
            out.append(f)
    return out


def stats(waivers: list[Waiver], today: date) -> str:
    """Which rules get waived most: a signal that the requirements may be too strict for some trades."""
    if not waivers:
        return "No waivers recorded."
    by_rule = Counter(w.rule for w in waivers)
    active = sum(w.until >= today for w in waivers)
    lines = [f"{len(waivers)} waivers ({active} active, {len(waivers) - active} expired) as of {today.isoformat()}", ""]
    for rule, n in by_rule.most_common():
        insureds = sorted({w.insured for w in waivers if w.rule == rule})
        lines.append(f"  {rule}  ×{n}  {', '.join(insureds)}")
    top, n = by_rule.most_common(1)[0]
    if n >= 3:
        lines += ["", f"{top} is waived {n} times: consider whether the requirement fits every trade."]
    return "\n".join(lines)
