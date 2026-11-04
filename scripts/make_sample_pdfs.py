"""Regenerate the fictional sample certificate PDFs in examples/pdfs/ (needs reportlab + pdfplumber).

    python scripts/make_sample_pdfs.py

Writes three versions of examples/cert_sample.json:
  northside-fillable.pdf  form fields (read with pypdf)
  northside-flat.pdf      text only (read with pdfplumber + regexes)
  northside-scanned.pdf   image only (read with Tesseract OCR)

The layout is a plain, made-up "certificate of insurance (sample)". It is deliberately NOT a
copy of any industry form.
"""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "examples" / "pdfs"
KINDS = [("general_liability", "GENERAL LIABILITY", "gl"), ("auto", "AUTOMOBILE LIABILITY", "au"),
         ("umbrella", "UMBRELLA / EXCESS", "um"), ("workers_comp", "WORKERS COMPENSATION", "wc")]


def label(limit: str) -> str:
    return limit.replace("_", " ").capitalize().replace("El ", "EL ")


def lines(cert: dict) -> list[tuple[str, str | None, str]]:
    """(text label, form field name or None, value) rows in reading order."""
    rows = [("CERTIFICATE OF INSURANCE (SAMPLE, FICTIONAL)", None, ""),
            ("Insured:", "insured", cert["insured"]),
            ("Producer:", "producer", cert["producer"]),
            ("Certificate holder:", "holder", cert["holder"]),
            ("Issued:", "issued", cert["issued"]),
            ("Description of operations:", "description", cert["description"])]
    by_kind = {c["kind"]: c for c in cert["coverages"]}
    for kind, head, ab in KINDS:
        c = by_kind[kind]
        rows.append((f"{head}  Policy: {c['policy_number']}  Effective: {c['effective']}  Expires: {c['expires']}",
                     None, ""))
        parts = [f"{label(k)}: ${v:,}" for k, v in c["limits"].items()]
        parts.append(f"Additional insured: {'Y' if c.get('additional_insured') else 'N'}")
        parts.append(f"Waiver of subrogation: {'Y' if c.get('waiver_of_subrogation') else 'N'}")
        rows.append(("    " + "  ".join(parts), None, ""))
    return rows


def flat(cert: dict, path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica", 9)
    y = 800
    for text, field, value in lines(cert):
        c.drawString(40, y, f"{text} {value}".rstrip())
        y -= 22
    c.save()


def fillable(cert: dict, path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica", 9)
    form = c.acroForm
    y = 800
    for text, field, value in lines(cert)[:6]:
        c.drawString(40, y, text)
        if field:
            form.textfield(name=field, value=value, x=170, y=y - 4, width=380, height=14, borderWidth=0,
                           fontSize=8)
        y -= 22
    by_kind = {k["kind"]: k for k in cert["coverages"]}
    for kind, head, ab in KINDS:
        cov = by_kind[kind]
        c.drawString(40, y, head)
        y -= 18
        x = 40
        for fld in ("policy_number", "effective", "expires", *cov["limits"]):
            v = cov.get(fld, cov["limits"].get(fld))
            c.drawString(x, y + 12, fld.replace("_", " "))
            form.textfield(name=f"{ab}_{fld}", value=str(v), x=x, y=y - 4, width=90, height=14,
                           borderWidth=0, fontSize=7)
            x += 95
        for fld in ("additional_insured", "waiver_of_subrogation"):
            c.drawString(x + 16, y + 12, fld.replace("_", " "))
            form.checkbox(name=f"{ab}_{fld}", x=x, y=y - 2, size=12, checked=bool(cov.get(fld)), buttonStyle="check")
            x += 95
        y -= 40
    c.save()


def scanned(src: Path, path: Path) -> None:
    import pdfplumber

    with pdfplumber.open(str(src)) as doc:
        img = doc.pages[0].to_image(resolution=300).original.convert("L")
    img.save(str(path), "PDF", resolution=300)


def main() -> None:
    cert = json.loads((ROOT / "examples" / "cert_sample.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    fillable(cert, OUT / "northside-fillable.pdf")
    flat(cert, OUT / "northside-flat.pdf")
    scanned(OUT / "northside-flat.pdf", OUT / "northside-scanned.pdf")
    print("wrote", ", ".join(p.name for p in sorted(OUT.glob("*.pdf"))))


if __name__ == "__main__":
    main()
