import importlib.util
import json
from pathlib import Path

import pytest

from coi_lint.accuracy import flatten
from coi_lint.cli import main
from coi_lint.extract import extract, load_fieldmap

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"
TRUTH = EX / "labelled" / "truth"


def _script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pdfgen():
    pytest.importorskip("reportlab")
    return _script("make_sample_pdfs")


def _cert(drop=()):
    cert = json.loads((EX / "cert_sample.json").read_text())
    cert["coverages"] = [c for c in cert["coverages"] if c["kind"] not in drop]
    return cert


def _labelled(tmp_path, pdfgen, certs):
    """Write labels to tmp/truth and render them (alternating fillable / flat) to tmp/pdfs."""
    (tmp_path / "truth").mkdir()
    (tmp_path / "pdfs").mkdir()
    for i, cert in enumerate(certs):
        (tmp_path / "truth" / f"c{i}.json").write_text(json.dumps(cert))
        (pdfgen.fillable if i % 2 == 0 else pdfgen.flat)(cert, tmp_path / "pdfs" / f"c{i}.pdf")
    return tmp_path / "pdfs"


def test_flatten_fills_unmarked_flags_only_for_labels():
    cov = {"kind": "auto", "policy_number": "AU-1", "effective": "2026-01-01", "expires": "2027-01-01",
           "limits": {"combined_single_limit": 1000000}}
    label = flatten({"insured": "X", "coverages": [cov]})
    assert label["coverages.auto.additional_insured"] is False
    assert label["coverages.auto.limits.combined_single_limit"] == 1000000
    assert "coverages.auto.additional_insured" not in flatten({"coverages": [cov]}, default_flags=False)


@pytest.mark.parametrize("render", ["fillable", "flat"])
def test_absent_coverage_is_not_unreadable(tmp_path, pdfgen, render, capsys):
    pdf = tmp_path / "c.pdf"
    getattr(pdfgen, render)(_cert(drop=("umbrella", "auto")), pdf)
    d = extract(pdf, load_fieldmap())
    assert d["_unreadable"] == []
    assert sorted(c["kind"] for c in d["coverages"]) == ["general_liability", "workers_comp"]
    # required-but-absent coverages are reported as missing (COI002), not as unreadable (COI009)
    main(["check", str(pdf), "--rules", str(EX / "requirements.yaml"), "--today", "2026-11-04", "--format", "json"])
    rules = {f["rule"] for f in json.loads(capsys.readouterr().out)["findings"]}
    assert "COI002" in rules and "COI009" not in rules


def test_accuracy_perfect_on_fillable_and_flat(tmp_path, pdfgen, capsys):
    pdfs = _labelled(tmp_path, pdfgen, [_cert(), _cert(drop=("umbrella",)), _cert(drop=("auto",))])
    assert main(["accuracy", str(pdfs), "--min-accuracy", "1.0", "--format", "json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["files"] == 3 and out["accuracy"] == 1.0 and out["passed"] and out["extras"] == 0
    assert set(out["by_method"]) == {"form", "text"}


def test_accuracy_reports_misses_and_fails_threshold(tmp_path, pdfgen, capsys):
    pdfs = _labelled(tmp_path, pdfgen, [_cert(), _cert()])
    label = tmp_path / "truth" / "c1.json"
    wrong = json.loads(label.read_text())
    wrong["insured"] = "Somebody Else (fictional)"
    label.write_text(json.dumps(wrong))
    assert main(["accuracy", str(pdfs), "--min-accuracy", "1.0"]) == 1
    out = capsys.readouterr().out
    assert "c1.pdf [text] insured: expected 'Somebody Else (fictional)'" in out and "FAIL" in out
    assert main(["accuracy", str(pdfs)]) == 0          # no threshold: report only
    capsys.readouterr()
    assert main(["accuracy", str(pdfs), "--format", "md"]) == 0
    assert "| form | 1 |" in capsys.readouterr().out


def test_accuracy_bad_input(tmp_path, pdfgen):
    pdf = tmp_path / "lonely.pdf"
    pdfgen.flat(_cert(), pdf)
    assert main(["accuracy", str(pdf)]) == 2                       # no label
    assert main(["accuracy", str(tmp_path / "missing")]) == 2
    (tmp_path / "lonely.json").write_text(json.dumps(_cert()))     # label next to the PDF also works
    assert main(["accuracy", str(pdf), "--min-accuracy", "95"]) == 2
    assert main(["accuracy", str(pdf), "--min-accuracy", "0.95"]) == 0


def test_committed_labelled_set_is_complete_and_fictional():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "certificate.schema.json").read_text())
    labels = sorted(TRUTH.glob("cert-*.json"))
    assert [p.stem for p in labels] == [f"cert-{i:02d}" for i in range(1, 31)]
    kinds = set()
    for p in labels:
        cert = json.loads(p.read_text())
        jsonschema.validate(cert, schema)
        assert cert["insured"].endswith("(fictional)") and cert["producer"].endswith("(fictional)")
        assert all("-0000" in c["policy_number"] for c in cert["coverages"])
        kinds.add(len(cert["coverages"]))
    assert len(kinds) > 1        # some certificates leave coverages out
    pytest.importorskip("reportlab")
    gen = _script("make_labelled_set")
    assert [gen.layout_for(f"cert-{i:02d}") for i in (1, 10, 11, 20, 21, 30)] == \
           ["fillable", "fillable", "flat", "flat", "scanned", "scanned"]
