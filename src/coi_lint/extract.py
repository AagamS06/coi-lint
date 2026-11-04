"""Read a certificate PDF into the normalised certificate model. Free and offline.

Three layers, tried in order:
  1. form fields (fillable PDFs) via pypdf
  2. the text layer via pdfplumber, matched with regular expressions
  3. OCR via Tesseract (pytesseract) for scanned, image-only PDFs, then the same regexes

Which field holds what is described in a field map (YAML), so new certificate layouts need a
new map, not new code. coi-lint never guesses: anything it can't read is listed in
`_unreadable`, and `check` turns that into a COI009 finding.

Field map format (see src/coi_lint/fieldmaps/sample.yaml):

    name: coi-lint-sample
    date_format: "%Y-%m-%d"              # how dates are written on this layout
    form_fields: {<pdf field name>: <model path>}
    text_patterns: {<regex with one group>: <model path>}

Model paths: insured, producer, holder, issued, description,
coverages.<kind>.policy_number|effective|expires, coverages.<kind>.limits.<name>,
coverages.<kind>.additional_insured|waiver_of_subrogation.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

FIELDMAP_DIR = Path(__file__).parent / "fieldmaps"
DEFAULT_FIELDMAP = FIELDMAP_DIR / "sample.yaml"
MAX_PDF_BYTES = 20 * 1024 * 1024        # refuse oversized files (untrusted input)
MAX_PAGES = 10
TRUE = {"/yes", "/on", "yes", "y", "x", "true", "1", "checked"}
FALSE = {"/off", "off", "no", "n", "false", "0", ""}


def load_fieldmap(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_FIELDMAP
    try:
        fm = yaml.safe_load(p.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"field map {p}: {exc}") from exc
    if not isinstance(fm, dict) or not (fm.get("form_fields") or fm.get("text_patterns")):
        raise ValueError(f"field map {p}: needs form_fields and/or text_patterns")
    return fm


def _parse(path: str, raw: str, date_format: str) -> Any:
    leaf = path.split(".")[-1]
    raw = raw.strip()
    if leaf in ("effective", "expires", "issued"):
        return datetime.strptime(raw, date_format).date().isoformat()  # noqa: DTZ007 (calendar date only, no time zone)
    if ".limits." in path:
        digits = re.sub(r"[^\d]", "", raw)
        if not digits:
            raise ValueError("no digits")
        return int(digits)
    if leaf in ("additional_insured", "waiver_of_subrogation"):
        v = raw.lower()
        if v in TRUE:
            return True
        if v in FALSE:
            return False
        raise ValueError(f"not a yes/no value: {raw!r}")
    if not raw:
        raise ValueError("empty")
    return raw


def _set(out: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    if parts[0] == "coverages":
        kind = parts[1]
        cov = out.setdefault("_cov", {}).setdefault(kind, {"kind": kind})
        if parts[2] == "limits":
            cov.setdefault("limits", {})[parts[3]] = value
        else:
            cov[parts[2]] = value
    else:
        out[parts[0]] = value


def _pdf_text(pdf: Path) -> tuple[str, str]:
    import pdfplumber

    with pdfplumber.open(str(pdf)) as doc:
        pages = doc.pages[:MAX_PAGES]
        text = "\n".join(p.extract_text() or "" for p in pages)
        if text.strip():
            return text, "text"
        try:
            import pytesseract
        except ImportError:
            return "", "none"
        ocr = []
        for p in pages:
            img = p.to_image(resolution=300).original
            ocr.append(pytesseract.image_to_string(img))
        return "\n".join(ocr), "ocr"


def extract(pdf: Path, fieldmap: dict[str, Any]) -> dict[str, Any]:
    """Return a certificate dict (same shape as examples/cert_sample.json) plus `_method` and `_unreadable`."""
    if not pdf.is_file():
        raise ValueError(f"{pdf} does not exist")
    if pdf.stat().st_size > MAX_PDF_BYTES:
        raise ValueError(f"{pdf} is larger than {MAX_PDF_BYTES // (1024 * 1024)} MB")
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    fmt = fieldmap.get("date_format", "%Y-%m-%d")
    out: dict[str, Any] = {"source": str(pdf)}
    unreadable: list[str] = []
    method = "none"

    try:
        fields = PdfReader(str(pdf)).get_fields() or {}
    except (PdfReadError, ValueError) as exc:
        raise ValueError(f"{pdf} is not a readable PDF: {exc}") from exc
    form_map = fieldmap.get("form_fields") or {}
    values = {name: fields[name].get("/V") for name in form_map if name in fields}
    if any(v not in (None, "", "/Off") for v in values.values()):
        method = "form"
        for name, path in form_map.items():
            raw = values.get(name)
            if raw is None:
                unreadable.append(path)
                continue
            try:
                _set(out, path, _parse(path, str(raw), fmt))
            except ValueError:
                unreadable.append(path)
    else:
        text, method = _pdf_text(pdf)
        for pattern, path in (fieldmap.get("text_patterns") or {}).items():
            m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if not m:
                unreadable.append(path)
                continue
            try:
                _set(out, path, _parse(path, m.group(1), fmt))
            except ValueError:
                unreadable.append(path)

    covs = []
    for kind, cov in out.pop("_cov", {}).items():
        if "effective" in cov and "expires" in cov:
            covs.append(cov)
        else:   # without dates a coverage can't be checked: report it instead of guessing
            unreadable.append(f"coverages.{kind} (dates)")
    out["coverages"] = covs
    out.setdefault("issued", out.get("issued") or "1970-01-01")
    for key in ("insured", "producer", "holder", "description"):
        out.setdefault(key, "")
    out["_method"] = method
    out["_unreadable"] = sorted(set(unreadable))
    return out


def load_documents(paths: list[Path], fieldmap: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Certificate dicts from JSON and/or PDF files and folders (searched recursively), in a stable order."""
    import json

    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(x for x in p.rglob("*") if x.suffix.lower() in (".json", ".pdf")))
        elif p.is_file():
            files.append(p)
        else:
            raise ValueError(f"{p} does not exist")
    if not files:
        raise ValueError("no certificate files (.json or .pdf) found")
    docs = []
    for f in files:
        if f.suffix.lower() == ".pdf":
            docs.append(extract(f, fieldmap or load_fieldmap()))
        else:
            try:
                d = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"certificate {f} is malformed: {exc}") from exc
            d["source"] = str(f)
            docs.append(d)
    return docs

