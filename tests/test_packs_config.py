from datetime import date
from pathlib import Path

import pytest

from coi_lint.cli import main
from coi_lint.config import load_requirements
from coi_lint.packs import load_pack

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"


def test_extends_merges_base_and_override():
    req, rules = load_requirements(EX / "requirements-strict.yaml")
    assert req.name.endswith("strict profile") and req.warn_days == 45
    assert req.holder == "Example Builders LLC"                        # inherited
    assert {c.kind for c in req.coverages} == {"general_liability", "auto", "umbrella", "workers_comp"}
    assert [r.id for r in rules] == ["SGC001", "SGC002", "SGC003", "SGC004"]


def test_insured_override_applies_by_substring():
    req, _ = load_requirements(EX / "requirements-strict.yaml", insured="Coastal Steel Erectors (fictional)")
    assert req.warn_days == 60


def test_extends_loop_is_an_error(tmp_path):
    (tmp_path / "a.yaml").write_text("extends: b.yaml\nname: a\n")
    (tmp_path / "b.yaml").write_text("extends: a.yaml\nname: b\n")
    with pytest.raises(ValueError, match="loop"):
        load_requirements(tmp_path / "a.yaml")


@pytest.mark.parametrize("body, msg", [
    ("rules:\n  - {id: COI999, check: coverage_present, coverage: auto}\n", "reserved"),
    ("rules:\n  - {id: ABC001, check: run_python}\n", "unknown check"),
    ("rules:\n  - {id: ABC001, check: limit_min, coverage: auto, limit: x}\n", "needs min"),
    ("rules:\n  - {id: ABC001, check: flag, coverage: auto, flag: on_fire}\n", "flag must be"),
    ("rules: nope\n", "rules:"),
])
def test_bad_packs_are_rejected(tmp_path, body, msg):
    p = tmp_path / "p.yaml"
    p.write_text(body)
    with pytest.raises(ValueError, match=msg):
        load_pack(p)


def test_pack_rules_run_and_skip_already_required_missing_coverage(capsys):
    rc = main(["check", str(EX / "certs" / "coastal-steel.json"), "--rules", str(EX / "requirements-strict.yaml"),
               "--today", "2026-11-04", "--format", "json"])
    out = capsys.readouterr().out
    assert rc == 1
    assert '"rule": "SGC001"' in out and '"rule": "SGC003"' in out
    assert '"rule": "SGC004"' not in out          # workers' comp missing: COI002 already reports it


def test_explain_builtin_and_pack(capsys):
    assert main(["explain", "COI005"]) == 0
    assert "How to fix" in capsys.readouterr().out
    assert main(["explain", "SGC002", "--rules", str(EX / "requirements-strict.yaml")]) == 0
    assert "pack: strict-gc-example" in capsys.readouterr().out
    assert main(["explain", "NOPE123"]) == 2


def test_every_failure_has_a_fix(capsys):
    main(["check", str(EX / "cert_sample.json"), "--rules", str(EX / "requirements-strict.yaml"),
          "--today", "2026-11-04", "--format", "json"])
    import json
    findings = json.loads(capsys.readouterr().out)["findings"]
    assert all(f["fix"] for f in findings if f["severity"] in ("fail", "warn"))
    assert date(2026, 11, 4)  # fixed date keeps the run reproducible
