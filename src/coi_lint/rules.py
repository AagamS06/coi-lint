"""Deterministic checks: a certificate against a requirements profile.

Every finding has a stable rule id so reports, tests and deficiency letters can
refer to it. No network calls, no AI: the same inputs always give the same output.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import Certificate, Requirements

LABELS = {
    "general_liability": "General liability",
    "auto": "Automobile liability",
    "umbrella": "Umbrella / excess",
    "workers_comp": "Workers' compensation",
}


@dataclass
class Finding:
    rule: str          # e.g. "COI003"
    severity: str      # "fail" | "warn" | "pass"
    coverage: str      # coverage kind or "certificate"
    message: str


def _label(kind: str) -> str:
    return LABELS.get(kind, kind.replace("_", " ").title())


def _money(n: int) -> str:
    return f"${n:,}"


def check(cert: Certificate, req: Requirements, today: date | None = None) -> list[Finding]:
    today = today or date.today()  # noqa: DTZ011 (local calendar date is intended)
    out: list[Finding] = []

    # COI001 certificate holder matches the requesting party
    if req.holder:
        if req.holder.lower() in cert.holder.lower():
            out.append(Finding("COI001", "pass", "certificate", f"Holder is {req.holder}"))
        else:
            out.append(Finding("COI001", "fail", "certificate",
                               f"Holder is '{cert.holder or 'blank'}', expected '{req.holder}'"))

    for cr in req.coverages:
        cov = cert.coverage(cr.kind)
        name = _label(cr.kind)
        # COI002 required coverage present
        if cov is None:
            out.append(Finding("COI002", "fail", cr.kind, f"{name}: not on certificate"))
            continue

        # COI003 / COI004 dates
        if cov.expires < today:
            out.append(Finding("COI003", "fail", cr.kind, f"{name}: expired {cov.expires.isoformat()}"))
        elif (cov.expires - today).days <= req.warn_days:
            out.append(Finding("COI004", "warn", cr.kind,
                               f"{name}: expires in {(cov.expires - today).days} days ({cov.expires.isoformat()})"))
        elif cov.effective > today:
            out.append(Finding("COI004", "warn", cr.kind, f"{name}: not effective until {cov.effective.isoformat()}"))
        else:
            out.append(Finding("COI003", "pass", cr.kind, f"{name}: in force until {cov.expires.isoformat()}"))

        # COI005 minimum limits
        for limit, minimum in cr.min_limits.items():
            have = cov.limits.get(limit)
            pretty = limit.replace("_", " ")
            if have is None:
                out.append(Finding("COI005", "fail", cr.kind, f"{name}: {pretty} limit missing (need {_money(minimum)})"))
            elif have < minimum:
                out.append(Finding("COI005", "fail", cr.kind,
                                   f"{name}: {pretty} {_money(have)} < required {_money(minimum)}"))
            else:
                out.append(Finding("COI005", "pass", cr.kind, f"{name}: {pretty} {_money(have)}"))

        # COI006 additional insured, COI007 waiver of subrogation
        if cr.additional_insured:
            ok = cov.additional_insured
            out.append(Finding("COI006", "pass" if ok else "fail", cr.kind,
                               f"{name}: additional insured {'marked' if ok else 'NOT marked'}"))
        if cr.waiver_of_subrogation:
            ok = cov.waiver_of_subrogation
            out.append(Finding("COI007", "pass" if ok else "fail", cr.kind,
                               f"{name}: waiver of subrogation {'marked' if ok else 'NOT marked'}"))

    # COI008 description of operations mentions the project
    for phrase in req.description_must_mention:
        ok = phrase.lower() in cert.description.lower()
        out.append(Finding("COI008", "pass" if ok else "fail", "certificate",
                           f"Description {'mentions' if ok else 'does not mention'} '{phrase}'"))
    return out


def verdict(findings: list[Finding]) -> str:
    if any(f.severity == "fail" for f in findings):
        return "DEFICIENT"
    if any(f.severity == "warn" for f in findings):
        return "COMPLIANT_WITH_WARNINGS"
    return "COMPLIANT"
