"""Renewal tracking across many certificates.

Collects every policy from a set of normalised certificates, works out how many days
each has left, and groups them into reminder windows (expired, 30, 60, 90 days).
Pure functions: the caller passes `today`, so results are reproducible.
"""

from __future__ import annotations

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


def load_certificates(paths: list[Path], fieldmap: dict | None = None) -> list[Certificate]:
    """Load certificates from JSON/PDF files and/or folders of them (searched recursively)."""
    from .extract import load_documents

    return [certificate_from_dict(d, source=str(d.get("source", ""))) for d in load_documents(paths, fieldmap)]


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
