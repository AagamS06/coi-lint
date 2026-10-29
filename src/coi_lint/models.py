"""Data model for a normalised certificate of insurance and a set of requirements.

Phase 0 reads certificates that are already normalised to JSON (see examples/).
PDF extraction (fillable form fields first, text fallback) arrives in Phase 1 and
must produce exactly this structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class Coverage:
    kind: str                          # "general_liability", "auto", "umbrella", "workers_comp"
    policy_number: str
    effective: date
    expires: date
    limits: dict[str, int] = field(default_factory=dict)   # e.g. {"each_occurrence": 1000000}
    additional_insured: bool = False
    waiver_of_subrogation: bool = False


@dataclass
class Certificate:
    insured: str
    producer: str
    holder: str
    issued: date
    coverages: list[Coverage]
    description: str = ""
    source: str = ""

    def coverage(self, kind: str) -> Coverage | None:
        return next((c for c in self.coverages if c.kind == kind), None)


@dataclass
class CoverageRequirement:
    kind: str
    min_limits: dict[str, int] = field(default_factory=dict)
    additional_insured: bool = False
    waiver_of_subrogation: bool = False


@dataclass
class Requirements:
    name: str
    holder: str
    warn_days: int
    coverages: list[CoverageRequirement]
    description_must_mention: list[str] = field(default_factory=list)


def _d(value: Any) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def certificate_from_dict(data: dict[str, Any], source: str = "") -> Certificate:
    try:
        covs = [
            Coverage(
                kind=c["kind"],
                policy_number=str(c.get("policy_number", "")),
                effective=_d(c["effective"]),
                expires=_d(c["expires"]),
                limits={k: int(v) for k, v in (c.get("limits") or {}).items()},
                additional_insured=bool(c.get("additional_insured", False)),
                waiver_of_subrogation=bool(c.get("waiver_of_subrogation", False)),
            )
            for c in data.get("coverages", [])
        ]
        return Certificate(
            insured=data["insured"],
            producer=data.get("producer", ""),
            holder=data.get("holder", ""),
            issued=_d(data["issued"]),
            coverages=covs,
            description=data.get("description", ""),
            source=source,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(f"certificate {source or '<input>'} is malformed: {exc}") from exc


def requirements_from_dict(data: dict[str, Any]) -> Requirements:
    try:
        return Requirements(
            name=data["name"],
            holder=data.get("holder", ""),
            warn_days=int(data.get("warn_days", 30)),
            coverages=[
                CoverageRequirement(
                    kind=c["kind"],
                    min_limits={k: int(v) for k, v in (c.get("min_limits") or {}).items()},
                    additional_insured=bool(c.get("additional_insured", False)),
                    waiver_of_subrogation=bool(c.get("waiver_of_subrogation", False)),
                )
                for c in data.get("coverages", [])
            ],
            description_must_mention=list(data.get("description_must_mention", [])),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(f"requirements file is malformed: {exc}") from exc
