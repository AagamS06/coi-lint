from datetime import date
from pathlib import Path

from coi_lint.cli import main
from coi_lint.export import ics, letters
from coi_lint.renewals import collect, due, load_certificates

EX = Path(__file__).resolve().parent.parent / "examples"
TODAY = date(2026, 10, 30)
PATHS = [EX / "cert_sample.json", EX / "certs"]


def all_renewals():
    return collect(load_certificates(PATHS), TODAY)


def test_loads_files_and_folders():
    assert len(load_certificates(PATHS)) == 3


def test_sorted_soonest_first_with_windows():
    r = all_renewals()
    assert [x.expires for x in r] == sorted(x.expires for x in r)
    first = r[0]
    assert first.policy_number == "WC-0000102" and first.days_left == -10 and first.window == "expired"
    auto = next(x for x in r if x.policy_number == "AU-0000002")
    assert auto.days_left == 16 and auto.window == "30"
    assert next(x for x in r if x.policy_number == "GL-0000101").window == "60"
    assert next(x for x in r if x.policy_number == "GL-0000201").window == "90"
    assert next(x for x in r if x.policy_number == "AU-0000203").window == "later"


def test_due_window_boundaries():
    r = all_renewals()
    assert {x.policy_number for x in due(r, 16)} == {"WC-0000102", "AU-0000002"}   # boundary day included
    assert "AU-0000203" not in {x.policy_number for x in due(r, 90)}


def test_kinds_filter():
    r = collect(load_certificates(PATHS), TODAY, kinds={"auto"})
    assert {x.coverage for x in r} == {"auto"}


def test_ics_has_alarms_and_skips_expired():
    cal = ics(all_renewals(), TODAY)
    assert cal.startswith("BEGIN:VCALENDAR\r\n") and cal.endswith("END:VCALENDAR\r\n")
    assert cal.count("BEGIN:VEVENT") == 8          # 9 policies, 1 already expired
    assert cal.count("BEGIN:VALARM") == 8 * 3
    for w in (90, 60, 30):
        assert f"TRIGGER;RELATED=START:-P{w}D" in cal
    assert "WC-0000102" not in cal
    assert "DTSTART;VALUE=DATE:20261115" in cal
    assert "Example Builders" not in cal               # only insured/producer details, no holder data needed


def test_letters_grouped_by_producer():
    out = letters(due(all_renewals(), 90))
    assert out.count("To: ") == 2
    sample = out.split("To: Sample Insurance Agency (fictional)")[1].split("-----")[0]
    assert "Northside Electric" in sample and "Coastal Steel" in sample
    assert "expired 2026-10-20" in out and "review before sending" in out


def test_cli_exit_codes_and_ics(tmp_path, capsys):
    cal = tmp_path / "renewals.ics"
    rc = main(["renewals", *map(str, PATHS), "--today", "2026-10-30", "--ics", str(cal), "--no-color"])
    out = capsys.readouterr().out
    assert rc == 1 and "1 expired, 1 within 30 days" in out and cal.exists()
    assert main(["renewals", str(EX / "certs" / "coastal-steel.json"), "--today", "2026-10-30"]) == 0
    assert main(["renewals", str(tmp_path / "nope")]) == 2
    assert main(["renewals", str(EX / "certs"), "--within", "-1"]) == 2
