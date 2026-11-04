"""Rule packs: extra rules written in YAML, so anyone can add checks without writing Python.

A pack is declarative on purpose: it can only use the check types below, so loading a
pack never runs code. Example:

    pack: strict-gc-example
    description: Illustrative extra checks a cautious general contractor might add.
    rules:
      - id: SGC001
        title: Umbrella of at least $5M
        severity: fail                 # fail | warn
        coverage: umbrella             # omit for certificate-level checks
        check: limit_min
        limit: each_occurrence
        min: 5000000
        why: Large jobs need more cover than the primary policy alone.
        fix: Ask the broker for an umbrella/excess policy of at least $5,000,000.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .models import Certificate
from .rules import RULES, Finding, _label, _money

CHECKS = {
    "coverage_present": set(),
    "limit_min": {"limit", "min"},
    "flag": {"flag"},
    "valid_for_days": {"days"},
    "description_contains": {"text"},
    "holder_contains": {"text"},
    "policy_number_present": set(),
}
FLAGS = {"additional_insured", "waiver_of_subrogation"}
ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}\d{3}$")


@dataclass
class PackRule:
    id: str
    title: str
    check: str
    severity: str = "fail"
    coverage: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    why: str = ""
    fix: str = ""
    pack: str = ""


def load_pack(path: Path) -> list[PackRule]:
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"rule pack {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise ValueError(f"rule pack {path}: needs a top-level 'rules:' list")  # noqa: TRY004 (user input error)
    name = str(data.get("pack") or path.stem)
    out: list[PackRule] = []
    for i, r in enumerate(data["rules"], 1):
        where = f"rule pack {path} rule #{i}"
        if not isinstance(r, dict):
            raise ValueError(f"{where}: must be a mapping")  # noqa: TRY004 (user input error)
        rid, check = str(r.get("id", "")), r.get("check")
        if not ID_RE.match(rid) or rid.startswith("COI"):
            raise ValueError(f"{where}: id '{rid}' must look like ABC123 and not start with COI (reserved)")
        if check not in CHECKS:
            raise ValueError(f"{where}: unknown check '{check}'. Use one of: {', '.join(CHECKS)}")
        missing = CHECKS[check] - set(r)
        if missing:
            raise ValueError(f"{where}: check '{check}' needs {', '.join(sorted(missing))}")
        if check == "flag" and r["flag"] not in FLAGS:
            raise ValueError(f"{where}: flag must be one of {', '.join(sorted(FLAGS))}")
        if check in {"limit_min", "flag", "valid_for_days", "coverage_present", "policy_number_present"} \
                and not r.get("coverage"):
            raise ValueError(f"{where}: check '{check}' needs a 'coverage'")
        sev = r.get("severity", "fail")
        if sev not in {"fail", "warn"}:
            raise ValueError(f"{where}: severity must be fail or warn")
        params = {k: r[k] for k in CHECKS[check]}
        if "min" in params:
            params["min"] = int(params["min"])
        if "days" in params:
            params["days"] = int(params["days"])
        out.append(PackRule(rid, str(r.get("title", rid)), check, sev, r.get("coverage"), params,
                            str(r.get("why", "")), str(r.get("fix", "")), name))
    return out


def register(rules: list[PackRule]) -> None:
    """Make pack rules available to `coi-lint explain`."""
    for r in rules:
        RULES[r.id] = {"title": f"{r.title} (pack: {r.pack})", "why": r.why or "Defined by a rule pack.",
                       "fix": r.fix or "See the rule pack."}


def run(cert: Certificate, rules: list[PackRule], today: date, required: set[str] | None = None) -> list[Finding]:
    """Run pack rules. If a rule's coverage is missing and the requirements already require that
    coverage, COI002 has flagged it, so the pack rule is skipped instead of repeating the problem."""
    out: list[Finding] = []
    for r in rules:
        scope = r.coverage or "certificate"
        cov = cert.coverage(r.coverage) if r.coverage else None
        name = _label(r.coverage) if r.coverage else "Certificate"
        if r.coverage and cov is None and r.coverage in (required or set()):
            continue
        if r.coverage and cov is None:
            out.append(Finding(r.id, r.severity, scope, f"{name}: not on certificate ({r.title})", r.fix))
            continue
        p = r.params
        if r.check == "coverage_present":
            ok, msg = True, f"{name}: present"
        elif r.check == "limit_min":
            have = cov.limits.get(p["limit"])
            pretty = p["limit"].replace("_", " ")
            ok = have is not None and have >= p["min"]
            msg = f"{name}: {pretty} {_money(have) if have is not None else 'missing'}" + \
                  ("" if ok else f" < required {_money(p['min'])}")
        elif r.check == "flag":
            ok = bool(getattr(cov, p["flag"]))
            msg = f"{name}: {p['flag'].replace('_', ' ')} {'marked' if ok else 'NOT marked'}"
        elif r.check == "valid_for_days":
            left = (cov.expires - today).days
            ok = left >= p["days"]
            msg = f"{name}: valid for {left} more days" + ("" if ok else f" (need at least {p['days']})")
        elif r.check == "policy_number_present":
            ok = bool(cov.policy_number.strip())
            msg = f"{name}: policy number {'shown' if ok else 'missing'}"
        else:  # description_contains / holder_contains
            hay = cert.description if r.check == "description_contains" else cert.holder
            ok = p["text"].lower() in hay.lower()
            what = "Description" if r.check == "description_contains" else "Holder"
            msg = f"{what} {'mentions' if ok else 'does not mention'} '{p['text']}'"
        out.append(Finding(r.id, "pass" if ok else r.severity, scope, msg, "" if ok else r.fix))
    return out
