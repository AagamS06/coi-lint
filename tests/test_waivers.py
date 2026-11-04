import json
from datetime import date
from pathlib import Path

import pytest

from coi_lint.cli import main
from coi_lint.rules import Finding, verdict
from coi_lint.waivers import Waiver, apply, load_waivers, stats

EX = Path(__file__).resolve().parent.parent / "examples"


def test_active_waiver_turns_finding_waived_and_changes_verdict():
    f = [Finding("COI007", "fail", "general_liability", "waiver NOT marked", "ask")]
    w = [Waiver("Northside", "COI007", "not needed for this trade", date(2027, 1, 1), "J", "general_liability")]
    out = apply(f, "Northside Electric Co", w, date(2026, 11, 4))
    assert out[0].severity == "waived" and "not needed" in out[0].waiver
    assert verdict(out) == "COMPLIANT"


def test_waiver_is_scoped_to_insured_rule_and_coverage():
    f = [Finding("COI007", "fail", "workers_comp", "x")]
    w = [Waiver("Northside", "COI007", "reason", date(2027, 1, 1), coverage="general_liability")]
    assert apply(f, "Northside", w, date(2026, 11, 4))[0].severity == "fail"
    assert apply(f, "Someone Else", [Waiver("Northside", "COI007", "r", date(2027, 1, 1))], date(2026, 11, 4))[0].severity == "fail"


def test_expired_waiver_is_flagged_not_applied():
    f = [Finding("COI003", "fail", "workers_comp", "expired")]
    out = apply(f, "Harbor Plumbing", [Waiver("Harbor", "COI003", "r", date(2026, 10, 25))], date(2026, 11, 4))
    assert out[0].severity == "fail" and "waiver expired 2026-10-25" in out[0].message


def test_load_requires_until(tmp_path):
    p = tmp_path / "w.yaml"
    p.write_text("waivers:\n  - {insured: A, rule: COI001, reason: because}\n")
    with pytest.raises(ValueError, match="until"):
        load_waivers(p)


def test_stats_and_cli(capsys):
    w = load_waivers(EX / "waivers.yaml")
    assert "1 active, 1 expired" in stats(w, date(2026, 11, 4))
    many = [Waiver(f"I{i}", "COI007", "r", date(2027, 1, 1)) for i in range(3)]
    assert "consider whether" in stats(many, date(2026, 11, 4))
    assert main(["waivers", str(EX / "waivers.yaml"), "--today", "2026-11-04"]) == 0
    main(["check", str(EX / "cert_sample.json"), "--rules", str(EX / "requirements.yaml"),
          "--waivers", str(EX / "waivers.yaml"), "--today", "2026-11-04", "--format", "json"])
    capsys.readouterr()
    main(["check", str(EX / "cert_sample.json"), "--rules", str(EX / "requirements.yaml"),
          "--waivers", str(EX / "waivers.yaml"), "--today", "2026-11-04", "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert any(f["severity"] == "waived" and f["rule"] == "COI007" for f in data["findings"])
