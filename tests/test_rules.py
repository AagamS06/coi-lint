import json
from datetime import date
from pathlib import Path

import yaml

from coi_lint.cli import main
from coi_lint.models import certificate_from_dict, requirements_from_dict
from coi_lint.rules import check, verdict

EX = Path(__file__).resolve().parent.parent / "examples"
TODAY = date(2026, 10, 29)


def load():
    cert = certificate_from_dict(json.loads((EX / "cert_sample.json").read_text()))
    req = requirements_from_dict(yaml.safe_load((EX / "requirements.yaml").read_text()))
    return cert, req


def test_sample_is_deficient_for_known_reasons():
    cert, req = load()
    f = check(cert, req, TODAY)
    fails = {(x.rule, x.coverage) for x in f if x.severity == "fail"}
    assert ("COI005", "umbrella") in fails            # $2M < $5M
    assert ("COI007", "general_liability") in fails   # waiver not marked
    assert verdict(f) == "DEFICIENT"


def test_expiring_auto_is_a_warning():
    cert, req = load()
    warns = [x for x in check(cert, req, TODAY) if x.severity == "warn"]
    assert any(x.rule == "COI004" and x.coverage == "auto" for x in warns)


def test_missing_coverage_and_expiry():
    cert, req = load()
    cert.coverages = [c for c in cert.coverages if c.kind != "workers_comp"]
    f = check(cert, req, date(2027, 4, 1))
    assert any(x.rule == "COI002" and x.coverage == "workers_comp" for x in f)
    assert any(x.rule == "COI003" and x.severity == "fail" for x in f)


def test_cli_exit_codes(capsys):
    args = [str(EX / "cert_sample.json"), "--rules", str(EX / "requirements.yaml"), "--today", "2026-10-29"]
    assert main(["check", *args, "--no-color"]) == 1
    assert "DEFICIENT" in capsys.readouterr().out
    assert main(["check", "missing.json", "--rules", str(EX / "requirements.yaml")]) == 2
