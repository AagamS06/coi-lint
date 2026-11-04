import email
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from coi_lint.extract import load_fieldmap
from coi_lint.inbox import StateFile, poll, process_message

EX = Path(__file__).resolve().parent.parent / "examples"


def mail(subject, attach=None, name="cert.pdf", mid="<1@test>"):
    m = EmailMessage()
    m["From"] = "Sam Broker <sam@broker.example>"
    m["To"] = "coi@builder.example"
    m["Subject"] = subject
    m["Message-ID"] = mid
    m.set_content("Certificate attached.")
    if attach is not None:
        m.add_attachment(attach, maintype="application", subtype="octet-stream", filename=name)
    return m.as_bytes()


class FakeIMAP:
    """Records every call so the test can prove nothing is sent, moved or deleted."""
    def __init__(self, messages):
        self.messages, self.appended, self.calls = messages, [], []

    def select(self, folder, readonly=False):
        self.calls.append(("select", folder, readonly))
        return "OK", [b"%d" % len(self.messages)]

    def search(self, charset, crit):
        return "OK", [b" ".join(str(i + 1).encode() for i in range(len(self.messages)))]

    def fetch(self, num, what):
        self.calls.append(("fetch", what))
        return "OK", [(b"1 (BODY[] {n})", self.messages[int(num) - 1]), b")"]

    def append(self, folder, flags, when, msg):
        self.appended.append((folder, flags, email.message_from_bytes(msg)))
        return "OK", [b""]


def handler(today=date(2026, 11, 4)):
    fm = load_fieldmap()
    return lambda raw: process_message(raw, EX / "requirements.yaml", [], today, fm, "coi@builder.example")


def test_pdf_certificate_gets_a_deficiency_draft_and_is_only_handled_once(tmp_path):
    pdf = (EX / "pdfs" / "northside-flat.pdf").read_bytes()
    imap = FakeIMAP([mail("COI for Harbor St", pdf), mail("Lunch?", None, mid="<2@test>")])
    state = StateFile(tmp_path / "state.json")
    log = poll(imap, "INBOX", "Drafts", state, handler())
    assert len(imap.appended) == 1
    folder, flags, draft = imap.appended[0]
    assert folder == "Drafts" and "\\Draft" in flags
    assert draft["To"] == "Sam Broker <sam@broker.example>" and draft["Subject"] == "Re: COI for Harbor St"
    assert draft["In-Reply-To"] == "<1@test>"
    body = draft.get_payload()
    assert "waiver of subrogation NOT marked" in body and "review before sending" in body
    assert any("DEFICIENT" in line for line in log) and any("skip" in line for line in log)
    assert ("select", "INBOX", True) in imap.calls and all(c[1] == "(BODY.PEEK[])" for c in imap.calls if c[0] == "fetch")
    poll(imap, "INBOX", "Drafts", StateFile(tmp_path / "state.json"), handler())
    assert len(imap.appended) == 1          # remembered, not drafted twice


def test_compliant_json_gets_a_thank_you_and_bad_file_gets_a_resend_request(tmp_path):
    good = (EX / "certs" / "coastal-steel.json").read_bytes()
    rules_ok = tmp_path / "req.yaml"
    rules_ok.write_text("name: Basic\nholder: Example Builders\ncoverages:\n  - kind: general_liability\n")
    draft, _ = process_message(mail("COI", good, name="coastal.json"), rules_ok, [], date(2026, 11, 4),
                               load_fieldmap(), "me@x.example")
    assert "meets the requirements" in draft.get_payload()
    draft, log = process_message(mail("COI", b"%PDF-broken", name="bad.pdf"), rules_ok, [], date(2026, 11, 4),
                                 load_fieldmap(), "me@x.example")
    assert "couldn't read bad.pdf" in draft.get_payload() and "unreadable" in log[0]
