import csv
import io
import json
from pathlib import Path

import pytest

from coi_lint import notify
from coi_lint.cli import main

EX = Path(__file__).resolve().parent.parent / "examples"
ARGS = [str(EX / "pdfs" / "northside-fillable.pdf"), str(EX / "certs"), "--rules", str(EX / "requirements.yaml"),
        "--waivers", str(EX / "waivers.yaml"), "--today", "2026-11-04"]


def test_report_formats(tmp_path, capsys):
    assert main(["report", *ARGS, "--format", "md"]) == 1
    md = capsys.readouterr().out
    assert md.startswith("# COI report") and "3 certificates checked" in md and "## Renewals due" in md
    assert "&#x27;" not in md
    assert main(["report", *ARGS, "--format", "json"]) == 1
    s = json.loads(capsys.readouterr().out)
    assert s["certificates"] == 3 and s["waived"] == 1 and s["renewals"][0]["days_left"] < 0
    main(["report", *ARGS, "--format", "csv"])
    rows = list(csv.DictReader(io.StringIO(capsys.readouterr().out)))
    assert len(rows) == 3 and {r["verdict"] for r in rows} <= {"DEFICIENT", "COMPLIANT", "COMPLIANT_WITH_WARNINGS"}
    out = tmp_path / "r.html"
    assert main(["report", *ARGS, "--format", "html", "--out", str(out)]) == 1
    page = out.read_text()
    assert page.startswith("<!doctype html>") and "prefers-color-scheme" in page and "<script" not in page


def test_slack_needs_env_and_posts(monkeypatch, capsys):
    assert main(["report", *ARGS, "--slack-env", "COI_TEST_HOOK"]) == 2          # env var missing
    monkeypatch.setenv("COI_TEST_HOOK", "http://insecure.example")
    assert main(["report", *ARGS, "--slack-env", "COI_TEST_HOOK"]) == 2          # https only
    sent = {}

    class Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout):
        sent["url"], sent["body"] = req.full_url, json.loads(req.data)
        return Resp()

    monkeypatch.setenv("COI_TEST_HOOK", "https://hooks.slack.com/services/T/B/X")
    monkeypatch.setattr(notify.urllib.request, "urlopen", fake_urlopen)
    capsys.readouterr()
    assert main(["report", *ARGS, "--slack-env", "COI_TEST_HOOK"]) == 1
    assert sent["url"].startswith("https://hooks.slack.com") and "3 certificates checked" in sent["body"]["text"]
    assert main(["renewals", str(EX / "certs"), "--today", "2026-11-04", "--slack-env", "COI_TEST_HOOK"]) == 1
    assert "renewals" in sent["body"]["text"]


def test_webhook_value_never_printed(monkeypatch, capsys):
    monkeypatch.setenv("COI_TEST_HOOK", "http://secret-token-value")
    main(["report", *ARGS, "--slack-env", "COI_TEST_HOOK"])
    assert "secret-token-value" not in capsys.readouterr().err
    with pytest.raises(ValueError):
        notify.webhook_from_env("COI_UNSET_VAR_XYZ")


def test_precommit_checks_each_file_and_returns_worst(capsys):
    from coi_lint.cli import precommit_main

    rc = precommit_main(["--rules", str(EX / "requirements.yaml"), "--today", "2026-06-01",
                         str(EX / "cert_sample.json"), str(EX / "certs" / "coastal-steel.json")])
    out = capsys.readouterr().out
    assert rc == 1
    assert "Northside" in out and "Coastal" in out
