"""Load a requirements file, following `extends:` and collecting `packs:`.

    extends: base-requirements.yaml   # path relative to this file; may itself extend another
    packs: [../packs/strict-gc-example.yaml]
    insured_overrides:                # per-insured tweaks, matched case-insensitively on a substring
      Northside Electric:
        warn_days: 45

Merging: scalar keys override; `coverages` merge by `kind` (an entry here replaces min_limits/flags
for that kind, a new kind is added); `description_must_mention` and `packs` are concatenated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import Requirements, requirements_from_dict
from .packs import PackRule, load_pack, register


def _merge(base: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in child.items():
        if k == "coverages":
            by_kind = {c["kind"]: dict(c) for c in base.get("coverages", [])}
            for c in v or []:
                by_kind[c["kind"]] = {**by_kind.get(c["kind"], {}), **c}
            out["coverages"] = list(by_kind.values())
        elif k in ("description_must_mention", "packs"):
            out[k] = list(base.get(k, [])) + [x for x in (v or []) if x not in base.get(k, [])]
        elif k == "insured_overrides":
            out[k] = {**base.get(k, {}), **(v or {})}
        else:
            out[k] = v
    return out


def _load_raw(path: Path, seen: tuple[Path, ...] = ()) -> dict[str, Any]:
    path = path.resolve()
    if path in seen:
        raise ValueError(f"requirements file {path} extends itself (loop)")
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"requirements file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"requirements file {path} must be a mapping")  # noqa: TRY004 (user input error, reported by the CLI)
    data["packs"] = [str((path.parent / p).resolve()) for p in data.get("packs", [])]
    parent = data.pop("extends", None)
    if parent:
        return _merge(_load_raw(path.parent / parent, seen + (path,)), data)
    return data


def load_requirements(path: Path, insured: str = "", extra_packs: list[Path] | None = None
                      ) -> tuple[Requirements, list[PackRule]]:
    raw = _load_raw(path)
    for key, override in (raw.get("insured_overrides") or {}).items():
        if insured and key.lower() in insured.lower():
            raw = _merge(raw, override)
    req = requirements_from_dict(raw)
    rules: list[PackRule] = []
    for p in [Path(x) for x in raw.get("packs", [])] + list(extra_packs or []):
        rules.extend(load_pack(p))
    ids = [r.id for r in rules]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"duplicate pack rule ids: {', '.join(dupes)}")
    register(rules)
    return req, rules
