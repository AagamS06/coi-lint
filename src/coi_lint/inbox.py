"""Inbox watcher: check certificates the moment they arrive, like a code-review bot does for PRs.

Runs on YOUR computer (or a server you control) against a mailbox over IMAP, so there's no
service to pay for. For each new email with a PDF or JSON certificate attached it:
  1. reads the certificate (coi-lint extract for PDFs),
  2. checks it against your requirements,
  3. writes a reply into your Drafts folder: a deficiency request, or a "received, compliant" note.

It NEVER sends email and never deletes or moves messages. Messages are read with BODY.PEEK, so
their read/unread state doesn't change. Processed Message-IDs are remembered in a small state
file so each email is only handled once.

The password comes from an environment variable you name (use an app password, e.g. a Gmail
app password), never from the command line or a file.
"""

from __future__ import annotations

import email
import email.policy
import imaplib
import json
import os
import tempfile
import time
from collections.abc import Callable
from datetime import date
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr
from pathlib import Path
from typing import Any

from . import report
from .config import load_requirements
from .extract import extract, load_fieldmap
from .models import certificate_from_dict
from .packs import run as run_packs
from .rules import Finding, check, verdict
from .waivers import Waiver, apply

MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024


def certificate_findings(data: dict[str, Any], rules_path: Path, waivers: list[Waiver], today: date,
                         extra_packs: list[Path] | None = None):
    """Shared by `check` and the inbox watcher: cert dict -> (cert, req, findings)."""
    cert = certificate_from_dict(data, source=str(data.get("source", "")))
    req, pack_rules = load_requirements(rules_path, insured=cert.insured, extra_packs=extra_packs)
    findings = check(cert, req, today) + run_packs(cert, pack_rules, today, {c.kind for c in req.coverages})
    for path in data.get("_unreadable", []):
        findings.append(Finding("COI009", "fail", "certificate", f"Could not read {path} from the PDF",
                                "Check this field by hand, or add it to the field map for this certificate layout."))
    if data.get("_method") == "ocr":
        findings.append(Finding("COI010", "warn", "certificate", "Read from a scanned image (OCR): verify the values",
                                "Compare policy numbers, dates and limits against the original before relying on them."))
    return cert, req, apply(findings, cert.insured, waivers, today)


def _attachments(msg: email.message.Message) -> list[tuple[str, bytes]]:
    out = []
    for part in msg.walk():
        name = part.get_filename() or ""
        if name.lower().endswith((".pdf", ".json")):
            payload = part.get_payload(decode=True) or b""
            if 0 < len(payload) <= MAX_ATTACHMENT_BYTES:
                out.append((Path(name).name, payload))
    return out


def build_reply(original: email.message.Message, sections: list[str], from_addr: str) -> EmailMessage:
    reply = EmailMessage()
    reply["From"] = from_addr
    reply["To"] = original.get("Reply-To") or original.get("From", "")
    subj = original.get("Subject", "certificate of insurance")
    reply["Subject"] = subj if subj.lower().startswith("re:") else f"Re: {subj}"
    if original.get("Message-ID"):
        reply["In-Reply-To"] = original["Message-ID"]
        reply["References"] = original["Message-ID"]
    reply["Date"] = formatdate(localtime=True)
    reply["Message-ID"] = make_msgid(domain="coi-lint.local")
    reply.set_content("\n\n".join(sections) + "\n\n(Draft prepared by coi-lint; review before sending.)\n")
    return reply


def process_message(raw: bytes, rules_path: Path, waivers: list[Waiver], today: date,
                    fieldmap: dict[str, Any], from_addr: str) -> tuple[EmailMessage | None, list[str]]:
    """Return (draft reply or None, log lines) for one raw email."""
    msg = email.message_from_bytes(raw, policy=email.policy.compat32)
    files = _attachments(msg)
    sender = parseaddr(msg.get("From", ""))[1] or "unknown sender"
    if not files:
        return None, [f"skip: no certificate attachment from {sender}"]
    sections, log = [], []
    with tempfile.TemporaryDirectory(prefix="coi-lint-") as tmp:
        for name, payload in files:
            path = Path(tmp) / name
            path.write_bytes(payload)
            try:
                data = extract(path, fieldmap) if name.lower().endswith(".pdf") else json.loads(payload)
                data["source"] = name
                cert, req, findings = certificate_findings(data, rules_path, waivers, today)
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                sections.append(f"We couldn't read {name}: {exc}. Please resend it as a PDF.")
                log.append(f"{name}: unreadable ({exc})")
                continue
            v = verdict(findings)
            log.append(f"{name}: {cert.insured} → {v}")
            if v == "DEFICIENT" or v == "COMPLIANT_WITH_WARNINGS":
                sections.append(report.letter(cert, req, findings).replace("(Draft generated by coi-lint; review before sending.)", "").strip())
            else:
                sections.append(f"Thanks, we've received and checked the certificate for {cert.insured} "
                                f"({name}). It meets the requirements for {req.name}.")
    return build_reply(msg, sections, from_addr), log


class StateFile:
    def __init__(self, path: Path):
        self.path = path
        self.seen: set[str] = set(json.loads(path.read_text())) if path.exists() else set()

    def save(self) -> None:
        self.path.write_text(json.dumps(sorted(self.seen)))


def poll(imap: Any, folder: str, drafts: str, state: StateFile, handle: Callable[[bytes], tuple[EmailMessage | None, list[str]]]
         ) -> list[str]:
    """One pass over the folder. `imap` is an imaplib.IMAP4-like object (a fake in tests)."""
    log = []
    typ, _ = imap.select(folder, readonly=True)
    if typ != "OK":
        raise ValueError(f"can't open folder {folder}")
    typ, data = imap.search(None, "ALL")
    for num in (data[0] or b"").split():
        typ, parts = imap.fetch(num, "(BODY.PEEK[])")
        raw = next((p[1] for p in parts if isinstance(p, tuple)), b"")
        mid = email.message_from_bytes(raw).get("Message-ID", f"<no-id-{num.decode()}>")
        if mid in state.seen:
            continue
        draft, lines = handle(raw)
        log += lines
        if draft is not None:
            imap.append(drafts, "(\\Draft)", imaplib.Time2Internaldate(time.time()), draft.as_bytes())
            log.append(f"draft reply saved to {drafts}")
        state.seen.add(mid)
    state.save()
    return log


def connect(host: str, user: str, password_env: str, port: int = 993) -> imaplib.IMAP4_SSL:
    password = os.environ.get(password_env, "")
    if not password:
        raise ValueError(f"environment variable {password_env} is not set (it should hold an app password)")
    imap = imaplib.IMAP4_SSL(host, port)
    imap.login(user, password)
    return imap


def run(host: str, user: str, password_env: str, folder: str, drafts: str, rules_path: Path,
        waivers: list[Waiver], state_path: Path, fieldmap_path: Path | None, once: bool, interval: int,
        today_fn: Callable[[], date] = date.today) -> None:
    fieldmap = load_fieldmap(fieldmap_path)
    state = StateFile(state_path)
    while True:
        imap = connect(host, user, password_env)
        try:
            for line in poll(imap, folder, drafts, state,
                             lambda raw: process_message(raw, rules_path, waivers, today_fn(), fieldmap, user)):
                print(line, flush=True)
        finally:
            try:
                imap.logout()
            except (imaplib.IMAP4.error, OSError):
                pass
        if once:
            return
        time.sleep(max(60, interval))
