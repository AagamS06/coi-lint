"""Deterministic checks: a certificate against a requirements profile.

Every finding has a stable rule id so reports, tests and letters can refer to it, and every
failing or warning finding carries a concrete `fix` suggestion (what to ask the broker for).
No network calls, no AI: the same inputs always give the same output.
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

# Documentation for `coi-lint explain`. Pack rules add their own entries at runtime.
RULES: dict[str, dict[str, str]] = {
    "COI001": {
        "title": "Certificate holder matches the requesting party",
        "why": "The certificate holder is who the certificate was issued to. If it names someone else, the "
               "certificate wasn't issued for your project and usually can't be relied on.",
        "fix": "Ask the broker to reissue the certificate with your exact legal name as certificate holder.",
    },
    "COI002": {
        "title": "Required coverage is on the certificate",
        "why": "Each coverage your contract requires (general liability, auto, umbrella, workers' comp) has to "
               "appear on the certificate. A missing line usually means the policy doesn't exist or wasn't listed.",
        "fix": "Ask the broker to add the missing coverage, or for proof of that policy on a separate certificate.",
    },
    "COI003": {
        "title": "Policy is in force (not expired)",
        "why": "An expired policy gives no cover for work done after its expiry date.",
        "fix": "Ask for a certificate showing the renewed policy and its new dates before work continues.",
    },
    "COI004": {
        "title": "Policy expiring soon, or not yet effective (warning)",
        "why": "A policy inside your warning window (warn_days) will need a renewed certificate soon; one that "
               "isn't effective yet doesn't cover work starting now.",
        "fix": "Diary the expiry (`coi-lint renewals --ics`) and ask for the renewed certificate before that date.",
    },
    "COI005": {
        "title": "Limit meets the contract minimum",
        "why": "Each limit (e.g. each occurrence, aggregate) must be at least what the contract requires.",
        "fix": "Ask the broker to raise the limit to the required minimum, or to show an umbrella/excess policy "
               "that covers the gap, then reissue the certificate.",
    },
    "COI006": {
        "title": "Additional insured is marked",
        "why": "Additional-insured status extends the policy to protect you for claims arising from their work.",
        "fix": "Ask the broker for an additional-insured endorsement naming you and to mark it on the certificate.",
    },
    "COI007": {
        "title": "Waiver of subrogation is marked",
        "why": "A waiver of subrogation stops their insurer from recovering a paid claim from you.",
        "fix": "Ask the broker for a waiver-of-subrogation endorsement in your favour and to mark it on the certificate.",
    },
    "COI008": {
        "title": "Description of operations mentions the project",
        "why": "The description box ties the certificate (and any endorsements) to your project or contract.",
        "fix": "Ask the broker to add your project name/address to the description of operations.",
    },
    "COI009": {
        "title": "A field could not be read from the PDF",
        "why": "coi-lint never guesses. If a field from the field map isn't found or can't be parsed, the "
               "certificate can't be fully checked, so it's flagged rather than assumed fine.",
        "fix": "Check that field by hand, or add/adjust the field map for this certificate layout "
               "(see src/coi_lint/fieldmaps/sample.yaml).",
    },
    "COI010": {
        "title": "Certificate was read from a scanned image (OCR) (warning)",
        "why": "OCR can misread characters (e.g. O for 0 in a policy number), so values may be wrong "
               "without looking unreadable.",
        "fix": "Compare policy numbers, dates and limits with the original, or ask for a digital (non-scanned) PDF.",
    },
}


@dataclass
class Finding:
    rule: str          # e.g. "COI003"
    severity: str      # "fail" | "warn" | "pass" | "waived"
    coverage: str      # coverage kind or "certificate"
    message: str
    fix: str = ""      # concrete next step for fail/warn findings
    waiver: str = ""   # reason, when a waiver turned a fail/warn into "waived"


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
                               f"Holder is '{cert.holder or 'blank'}', expected '{req.holder}'",
                               f"Ask the broker to reissue the certificate naming '{req.holder}' as certificate holder."))

    for cr in req.coverages:
        cov = cert.coverage(cr.kind)
        name = _label(cr.kind)
        # COI002 required coverage present
        if cov is None:
            out.append(Finding("COI002", "fail", cr.kind, f"{name}: not on certificate",
                               f"Ask the broker to add {name.lower()} to the certificate (or send proof of that policy)."))
            continue

        # COI003 / COI004 dates
        if cov.expires < today:
            out.append(Finding("COI003", "fail", cr.kind, f"{name}: expired {cov.expires.isoformat()}",
                               f"Ask for a certificate showing the renewed {name.lower()} policy before work continues."))
        elif (cov.expires - today).days <= req.warn_days:
            out.append(Finding("COI004", "warn", cr.kind,
                               f"{name}: expires in {(cov.expires - today).days} days ({cov.expires.isoformat()})",
                               f"Ask for the renewed {name.lower()} certificate before {cov.expires.isoformat()}."))
        elif cov.effective > today:
            out.append(Finding("COI004", "warn", cr.kind, f"{name}: not effective until {cov.effective.isoformat()}",
                               f"Confirm cover for work before {cov.effective.isoformat()}, or hold the start date."))
        else:
            out.append(Finding("COI003", "pass", cr.kind, f"{name}: in force until {cov.expires.isoformat()}"))

        # COI005 minimum limits
        for limit, minimum in cr.min_limits.items():
            have = cov.limits.get(limit)
            pretty = limit.replace("_", " ")
            if have is None:
                out.append(Finding("COI005", "fail", cr.kind, f"{name}: {pretty} limit missing (need {_money(minimum)})",
                                   f"Ask the broker to show the {name.lower()} {pretty} limit (at least {_money(minimum)})."))
            elif have < minimum:
                out.append(Finding("COI005", "fail", cr.kind,
                                   f"{name}: {pretty} {_money(have)} < required {_money(minimum)}",
                                   f"Ask the broker to raise {name.lower()} {pretty} to at least {_money(minimum)} "
                                   f"(or show an excess policy covering the {_money(minimum - have)} gap)."))
            else:
                out.append(Finding("COI005", "pass", cr.kind, f"{name}: {pretty} {_money(have)}"))

        # COI006 additional insured, COI007 waiver of subrogation
        if cr.additional_insured:
            ok = cov.additional_insured
            out.append(Finding("COI006", "pass" if ok else "fail", cr.kind,
                               f"{name}: additional insured {'marked' if ok else 'NOT marked'}",
                               "" if ok else f"Ask for an additional-insured endorsement on {name.lower()}, marked on the certificate."))
        if cr.waiver_of_subrogation:
            ok = cov.waiver_of_subrogation
            out.append(Finding("COI007", "pass" if ok else "fail", cr.kind,
                               f"{name}: waiver of subrogation {'marked' if ok else 'NOT marked'}",
                               "" if ok else f"Ask for a waiver-of-subrogation endorsement on {name.lower()}, marked on the certificate."))

    # COI008 description of operations mentions the project
    for phrase in req.description_must_mention:
        ok = phrase.lower() in cert.description.lower()
        out.append(Finding("COI008", "pass" if ok else "fail", "certificate",
                           f"Description {'mentions' if ok else 'does not mention'} '{phrase}'",
                           "" if ok else f"Ask the broker to add '{phrase}' to the description of operations."))
    return out


def verdict(findings: list[Finding]) -> str:
    """Waived findings never count against the certificate."""
    if any(f.severity == "fail" for f in findings):
        return "DEFICIENT"
    if any(f.severity == "warn" for f in findings):
        return "COMPLIANT_WITH_WARNINGS"
    return "COMPLIANT"


def explain(rule_id: str) -> str:
    """Plain-English documentation for one rule id (built-in or from a loaded pack)."""
    r = RULES.get(rule_id.upper())
    if r is None:
        known = ", ".join(sorted(RULES))
        raise ValueError(f"unknown rule '{rule_id}'. Known rules: {known}")
    return f"{rule_id.upper()} — {r['title']}\n\nWhy it matters: {r['why']}\n\nHow to fix: {r['fix']}"
