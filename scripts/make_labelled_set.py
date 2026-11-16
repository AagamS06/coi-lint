"""Build the labelled extraction-accuracy set in examples/labelled/ (needs reportlab + pdfplumber).

    python scripts/make_labelled_set.py            # render the PDFs from the committed labels
    python scripts/make_labelled_set.py --labels   # (maintainers) regenerate the labels themselves

Layout:
  examples/labelled/truth/cert-NN.json   the label: the exact certificate (committed)
  examples/labelled/pdfs/cert-NN.pdf     the rendered PDF (generated, git-ignored)

30 fictional certificates: cert-01..10 fillable, cert-11..20 flat (text layer), cert-21..30 scanned
(image only, read by OCR). Labels validate against schemas/certificate.schema.json.
Values vary (names with punctuation, limits, dates, yes/no marks, missing coverages) so the
field map is tested on more than one certificate. Everything is made up; the layout is the
repo's own sample layout, not an industry form. Score extraction with:

    coi-lint accuracy examples/labelled/pdfs
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_sample_pdfs import fillable, flat, scanned

ROOT = Path(__file__).resolve().parent.parent
SET = ROOT / "examples" / "labelled"
TRUTH = SET / "truth"
PDFS = SET / "pdfs"
COUNT = 30
LAYOUTS = ("fillable", "flat", "scanned")

INSUREDS = ["Northgate Roofing", "Blue Gum Plumbing & Gas", "Parramatta Paving", "O'Neill Scaffolding",
            "Riverbend Glazing", "Summit Fire Protection", "Ironbark Concrete", "Harbourline Electrical",
            "Wattle Joinery", "Red Cedar Landscapes", "Granite & Co Stonework", "Kestrel Lifts",
            "Westside Demolition", "Saltbush HVAC", "Bridgewater Painting", "Lantern Signage",
            "Eastwood Tiling", "Coral Bay Pools", "Highline Cranes", "Banksia Insulation",
            "Mill Street Drywall", "Copperleaf Solar", "Two Rivers Excavation", "Pinecrest Fencing",
            "Old Quarry Masonry", "Clearview Windows", "Tallowwood Flooring", "Driftwood Carpentry",
            "Silver Creek Steel", "Fernhill Waterproofing"]
PRODUCERS = ["Sample Insurance Agency", "Example Brokers Pty", "Placeholder Risk Partners", "Demo Cover Group"]
HOLDERS = ["Example Builders LLC", "Sample Developments Inc", "Placeholder Property Trust"]
SITES = ["120 Harbor St fit-out", "Level 3, 45 Example Rd", "Riverside Stage 2", "Unit 7, 9 Placeholder Ave"]
LIMITS = {
    "general_liability": {"each_occurrence": [1_000_000, 2_000_000, 5_000_000],
                          "general_aggregate": [2_000_000, 4_000_000, 10_000_000]},
    "auto": {"combined_single_limit": [500_000, 1_000_000, 2_000_000]},
    "umbrella": {"each_occurrence": [1_000_000, 5_000_000, 10_000_000]},
    "workers_comp": {"el_each_accident": [500_000, 1_000_000]},
}
PREFIX = {"general_liability": "GL", "auto": "AU", "umbrella": "UM", "workers_comp": "WC"}


def make_label(i: int, rng: random.Random) -> dict:
    issued = date(2026, 1, 5) + timedelta(days=rng.randrange(0, 300))
    kinds = ["general_liability"] + [k for k in ("auto", "umbrella", "workers_comp") if rng.random() < 0.75]
    coverages = []
    for n, kind in enumerate(kinds, start=1):
        effective = issued - timedelta(days=rng.randrange(0, 200))
        coverages.append({
            "kind": kind,
            "policy_number": f"{PREFIX[kind]}-0000{i:02d}{n}",
            "effective": effective.isoformat(),
            "expires": effective.replace(year=effective.year + 1).isoformat(),
            "limits": {name: rng.choice(opts) for name, opts in LIMITS[kind].items()},
            "additional_insured": rng.random() < 0.6,
            "waiver_of_subrogation": rng.random() < 0.5,
        })
    return {
        "insured": f"{INSUREDS[i - 1]} (fictional)",
        "producer": f"{rng.choice(PRODUCERS)} (fictional)",
        "holder": rng.choice(HOLDERS),
        "issued": issued.isoformat(),
        "description": f"{rng.choice(['Works', 'Installation', 'Maintenance'])} at {rng.choice(SITES)}.",
        "coverages": coverages,
    }


def write_labels() -> None:
    rng = random.Random(2026)
    TRUTH.mkdir(parents=True, exist_ok=True)
    for i in range(1, COUNT + 1):
        (TRUTH / f"cert-{i:02d}.json").write_text(json.dumps(make_label(i, rng), indent=2) + "\n")
    print(f"wrote {COUNT} labels to {TRUTH.relative_to(ROOT)}")


def layout_for(stem: str) -> str:
    """cert-01..10 → fillable, 11..20 → flat, 21..30 → scanned."""
    return LAYOUTS[min(2, (int(stem.split("-")[-1]) - 1) // 10)]


def render() -> None:
    labels = sorted(TRUTH.glob("cert-*.json"))
    if not labels:
        raise SystemExit("no labels found: run with --labels first")
    PDFS.mkdir(parents=True, exist_ok=True)
    for lab in labels:
        cert = json.loads(lab.read_text())
        out = PDFS / f"{lab.stem}.pdf"
        layout = layout_for(lab.stem)
        if layout == "fillable":
            fillable(cert, out)
        elif layout == "flat":
            flat(cert, out)
        else:
            tmp = PDFS / f"{lab.stem}.flat.tmp.pdf"
            flat(cert, tmp)
            scanned(tmp, out)
            tmp.unlink()
    print(f"rendered {len(labels)} PDFs to {PDFS.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", action="store_true", help="regenerate the labels (truth/*.json) before rendering")
    a = ap.parse_args()
    if a.labels:
        write_labels()
    render()


if __name__ == "__main__":
    main()
