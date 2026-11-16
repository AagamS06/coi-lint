"""Measure how accurately PDF extraction reads certificates, against hand-checked labels.

A labelled set is a folder of certificate PDFs plus, for each `NAME.pdf`, a label `NAME.json`
holding the exact certificate (same shape as examples/cert_sample.json). The label is looked for
next to the PDF first, then in a sibling `truth/` folder (examples/labelled/ uses that layout).

Every value in the label is one field (insured, issued, coverages.auto.limits.combined_single_limit,
...). A field is correct only when the extracted value equals the label exactly; unreadable or
different values are misses. Values extracted that the label doesn't have are counted as extras
(e.g. a coverage read from a certificate that doesn't carry it). Accuracy = correct / labelled fields.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .extract import extract

SCALARS = ("insured", "producer", "holder", "issued", "description")
COVERAGE_KEYS = ("policy_number", "effective", "expires")
FLAGS = ("additional_insured", "waiver_of_subrogation")


def flatten(cert: dict[str, Any], default_flags: bool = True) -> dict[str, Any]:
    """Certificate dict → {field path: value}; keys starting with `_` are ignored.

    Labels leave a yes/no mark out when it is "no", so `default_flags` fills those in as False.
    Extracted certificates use default_flags=False: a mark that wasn't read must not score as "no".
    """
    out: dict[str, Any] = {k: str(cert[k]) for k in SCALARS if cert.get(k) not in (None, "")}
    for cov in cert.get("coverages") or []:
        base = f"coverages.{cov['kind']}"
        for k in COVERAGE_KEYS:
            if k in cov:
                out[f"{base}.{k}"] = str(cov[k])
        for name, value in (cov.get("limits") or {}).items():
            out[f"{base}.limits.{name}"] = int(value)
        for k in FLAGS:
            if k in cov or default_flags:
                out[f"{base}.{k}"] = bool(cov.get(k, False))
    return out


@dataclass
class FileResult:
    pdf: str
    method: str
    seconds: float
    fields: int
    correct: int
    misses: list[dict[str, Any]] = field(default_factory=list)
    extras: list[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.fields if self.fields else 1.0


def find_label(pdf: Path) -> Path | None:
    for cand in (pdf.with_suffix(".json"), pdf.parent.parent / "truth" / f"{pdf.stem}.json"):
        if cand.is_file():
            return cand
    return None


def collect(paths: list[Path]) -> list[tuple[Path, Path]]:
    """(pdf, label) pairs from PDF files and/or folders (searched recursively), in a stable order."""
    pdfs: list[Path] = []
    for p in paths:
        if p.is_dir():
            pdfs.extend(sorted(x for x in p.rglob("*") if x.suffix.lower() == ".pdf"))
        elif p.is_file():
            pdfs.append(p)
        else:
            raise ValueError(f"{p} does not exist")
    pairs = []
    for pdf in pdfs:
        label = find_label(pdf)
        if label is None:
            raise ValueError(f"no label for {pdf}: expected {pdf.stem}.json next to it or in ../truth/")
        pairs.append((pdf, label))
    if not pairs:
        raise ValueError("no PDF files found")
    return pairs


def score_one(pdf: Path, label: Path, fieldmap: dict[str, Any]) -> FileResult:
    try:
        truth = flatten(json.loads(label.read_text()))
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise ValueError(f"label {label} is malformed: {exc}") from exc
    start = time.perf_counter()
    data = extract(pdf, fieldmap)
    seconds = time.perf_counter() - start
    unreadable = set(data.get("_unreadable", []))
    got = {k: v for k, v in flatten(data, default_flags=False).items() if k not in unreadable}
    res = FileResult(str(pdf), data["_method"], seconds, len(truth), 0)
    for path, want in truth.items():
        if path in got and got[path] == want:
            res.correct += 1
        else:
            res.misses.append({"field": path, "expected": want, "got": got.get(path)})
    res.extras = sorted(set(got) - set(truth))
    return res


def run(paths: list[Path], fieldmap: dict[str, Any]) -> list[FileResult]:
    return [score_one(pdf, label, fieldmap) for pdf, label in collect(paths)]


def summary(results: list[FileResult]) -> dict[str, Any]:
    total = sum(r.fields for r in results)
    correct = sum(r.correct for r in results)
    by_method: dict[str, list[FileResult]] = defaultdict(list)
    for r in results:
        by_method[r.method].append(r)
    miss_count: dict[str, int] = defaultdict(int)
    for r in results:
        for m in r.misses:
            # group per field type, e.g. coverages.*.expires, so the weakest pattern stands out
            parts = m["field"].split(".")
            key = ".".join(["coverages", "*", *parts[2:]]) if parts[0] == "coverages" else m["field"]
            miss_count[key] += 1
    return {
        "files": len(results),
        "fields": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 1.0,
        "extras": sum(len(r.extras) for r in results),
        "seconds": round(sum(r.seconds for r in results), 2),
        "by_method": {
            m: {"files": len(rs), "fields": sum(r.fields for r in rs), "correct": sum(r.correct for r in rs),
                "accuracy": round(sum(r.correct for r in rs) / max(1, sum(r.fields for r in rs)), 4),
                "seconds": round(sum(r.seconds for r in rs), 2)}
            for m, rs in sorted(by_method.items())
        },
        "weakest_fields": dict(sorted(miss_count.items(), key=lambda kv: (-kv[1], kv[0]))[:10]),
    }


def as_json(results: list[FileResult], min_accuracy: float | None) -> str:
    s = summary(results)
    s["min_accuracy"] = min_accuracy
    s["passed"] = min_accuracy is None or s["accuracy"] >= min_accuracy
    s["results"] = [{"pdf": r.pdf, "method": r.method, "seconds": round(r.seconds, 3), "fields": r.fields,
                     "correct": r.correct, "accuracy": round(r.accuracy, 4), "misses": r.misses, "extras": r.extras}
                    for r in results]
    return json.dumps(s, indent=2)


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def as_text(results: list[FileResult], min_accuracy: float | None, show_misses: int = 10, md: bool = False) -> str:
    s = summary(results)
    lines = []
    h = "## " if md else ""
    lines.append(f"{h}coi-lint extraction accuracy: {_pct(s['accuracy'])} "
                 f"({s['correct']}/{s['fields']} fields, {s['files']} files, {s['seconds']} s)")
    lines.append("")
    if md:
        lines += ["| Method | Files | Fields correct | Accuracy | Time |", "|---|---|---|---|---|"]
        for m, b in s["by_method"].items():
            lines.append(f"| {m} | {b['files']} | {b['correct']}/{b['fields']} | {_pct(b['accuracy'])} | {b['seconds']} s |")
    else:
        for m, b in s["by_method"].items():
            lines.append(f"  {m:<6} {b['files']:>3} files  {b['correct']:>4}/{b['fields']:<4} {_pct(b['accuracy']):>6}"
                         f"  {b['seconds']} s")
    if s["extras"]:
        lines += ["", f"Extra fields read that the labels don't have: {s['extras']}"]
    misses = [(r, m) for r in results for m in r.misses]
    if misses:
        lines += ["", "Weakest fields: " + ", ".join(f"{k} ({v})" for k, v in s["weakest_fields"].items())]
        lines += ["", f"Misses (first {min(show_misses, len(misses))} of {len(misses)}):"]
        for r, m in misses[:show_misses]:
            lines.append(f"  {'- ' if md else ''}{Path(r.pdf).name} [{r.method}] {m['field']}: "
                         f"expected {m['expected']!r}, got {m['got']!r}")
    if min_accuracy is not None:
        ok = s["accuracy"] >= min_accuracy
        lines += ["", f"{'PASS' if ok else 'FAIL'}: accuracy {_pct(s['accuracy'])} "
                      f"{'>=' if ok else '<'} required {_pct(min_accuracy)}"]
    return "\n".join(lines)
