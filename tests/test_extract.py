import json
import shutil
from pathlib import Path

import pytest

from coi_lint.cli import main
from coi_lint.extract import extract, load_fieldmap

EX = Path(__file__).resolve().parent.parent / "examples"
TRUTH = json.loads((EX / "cert_sample.json").read_text())


def same_as_truth(d):
    assert {k: d[k] for k in ("insured", "producer", "holder", "issued", "description")} == \
           {k: TRUTH[k] for k in ("insured", "producer", "holder", "issued", "description")}
    got = {c["kind"]: c for c in d["coverages"]}
    for c in TRUTH["coverages"]:
        g = got[c["kind"]]
        assert (g["policy_number"], g["effective"], g["expires"]) == (c["policy_number"], c["effective"], c["expires"])
        assert g["limits"] == c["limits"]
        assert g["additional_insured"] == bool(c.get("additional_insured"))
        assert g["waiver_of_subrogation"] == bool(c.get("waiver_of_subrogation"))


@pytest.mark.parametrize("name, method", [("northside-fillable.pdf", "form"), ("northside-flat.pdf", "text")])
def test_fillable_and_flat_pdfs_read_exactly(name, method):
    d = extract(EX / "pdfs" / name, load_fieldmap())
    assert d["_method"] == method and d["_unreadable"] == []
    same_as_truth(d)


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract not installed")
def test_scanned_pdf_uses_ocr_and_is_flagged(capsys):
    d = extract(EX / "pdfs" / "northside-scanned.pdf", load_fieldmap())
    assert d["_method"] == "ocr" and d["insured"] == TRUTH["insured"]
    main(["check", str(EX / "pdfs" / "northside-scanned.pdf"), "--rules", str(EX / "requirements.yaml"),
          "--today", "2026-11-04", "--format", "json"])
    assert '"rule": "COI010"' in capsys.readouterr().out


def test_unreadable_fields_become_coi009(tmp_path, capsys):
    fm = tmp_path / "fm.yaml"
    fm.write_text("name: t\ntext_patterns:\n  'Insured:\\s*(.+?)\\s*\\n': insured\n  'Nonexistent:\\s*(\\S+)': producer\n"
                  "  'GENERAL LIABILITY\\s+Policy:\\s*(\\S+)': coverages.general_liability.policy_number\n")
    d = extract(EX / "pdfs" / "northside-flat.pdf", __import__("coi_lint.extract", fromlist=["x"]).load_fieldmap(fm))
    assert "producer" in d["_unreadable"] and "coverages.general_liability (dates)" in d["_unreadable"]
    rc = main(["check", str(EX / "pdfs" / "northside-flat.pdf"), "--rules", str(EX / "requirements.yaml"),
               "--fieldmap", str(fm), "--today", "2026-11-04", "--format", "json"])
    assert rc == 1 and '"rule": "COI009"' in capsys.readouterr().out


def test_extract_cli_and_bad_input(tmp_path, capsys):
    assert main(["extract", str(EX / "pdfs" / "northside-flat.pdf")]) == 0
    assert json.loads(capsys.readouterr().out)["insured"] == TRUTH["insured"]
    bad = tmp_path / "x.pdf"
    bad.write_bytes(b"not a pdf")
    assert main(["extract", str(bad)]) == 2
    assert main(["extract", str(tmp_path / "missing.pdf")]) == 2


def test_check_pdf_matches_check_json(capsys):
    args = ["--rules", str(EX / "requirements.yaml"), "--today", "2026-11-04", "--format", "json"]
    main(["check", str(EX / "cert_sample.json"), *args])
    from_json = json.loads(capsys.readouterr().out)
    main(["check", str(EX / "pdfs" / "northside-fillable.pdf"), *args])
    from_pdf = json.loads(capsys.readouterr().out)
    assert from_json["verdict"] == from_pdf["verdict"] and from_json["findings"] == from_pdf["findings"]
