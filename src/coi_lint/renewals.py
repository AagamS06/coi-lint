"""Renewal tracking across many certificates.

Collects every policy from a set of normalised certificates, works out how many days
each has left, and groups them into reminder windows (expired, 30, 60, 90 days).
Pure functions: the caller passes `today`, so results are reproducible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .models import Certificate, certificate_from_dict
from .rules import LABELS

WINDOWS = (30, 60, 90)          # reminder windows, in days before expiry


@dataclass
class Renewal:
    insured: str
    producer: str
    coverage: str               # coverage kind, e.g. "auto"
    policy_number: str
    expires: date
    days_left: int              # negative = already expired
    source: str

    @property
    def label(self) -> str:
        return LABELS.get(self.coverage, self.coverage.replace("_", " ").title())

    @property
    def window(self) -> str:
        """'expired', '30', '60', '90' or 'later'."""
        if self.days_left < 0:
            return "expired"
        for w in WINDOWS:
            if self.days_left <= w:
                return str(w)
        return "later"


def load_certificates(paths: list[Path]) -> list[Certificate]:
    """Load certificates from JSON files and/or folders of JSON files (searched recursively)."""
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.rglob("*.json")))
        elif p.is_file():
            files.append(p)
        else:
            raise ValueError(f"{p} does not exist")
    if not files:
        raise ValueError("no certificate JSON files found")
    certs = []
    for f in files:
        try:
            data = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"certificate {f} is malformed: {exc}") from exc
        certs.append(certificate_from_dict(data, source=str(f)))
    return certs


def collect(certs: list[Certificate], today: date, kinds: set[str] | None = None) -> list[Renewal]:
    """Every policy on every certificate, soonest expiry first. `kinds` limits to those coverage kinds."""
    out = [
        Renewal(c.insured, c.producer, cov.kind, cov.policy_number, cov.expires,
                (cov.expires - today).days, c.source)
        for c in certs
        for cov in c.coverages
        if kinds is None or cov.kind in kinds
    ]
    return sorted(out, key=lambda r: (r.expires, r.insured, r.coverage))


def due(renewals: list[Renewal], within: int) -> list[Renewal]:
    """Policies that are expired or expire within `within` days."""
    return [r for r in renewals if r.days_left <= within]
