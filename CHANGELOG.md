# Changelog

## v0.2.0 — 2026-10-30
Renewal tracking, based on feedback from someone working in compliance: the chasing starts all over again every renewal cycle.

- New `coi-lint renewals <files/dirs>` command: every policy across many certificates, soonest expiry first, grouped into expired / 30 / 60 / 90-day windows. `--within`, `--rules` (only required coverages), `--format text|json|letter`. Exit code `1` if anything shown has expired.
- `--ics renewals.ics`: calendar file with one all-day event per upcoming expiry and reminders 90, 60 and 30 days before. Stable UIDs, so re-importing updates events instead of duplicating them.
- `--format letter`: one renewal-request draft per broker, listing all their clients' policies due. Drafts only, never sent.
- Two more fictional example certificates in `examples/certs/`; 7 new tests (11 total).
- SKILL.md teaches agents the renewals workflow.

## v0.1.0 — 2026-10-29
- `coi-lint check`: 8 deterministic rules (COI001–COI008), text / JSON / deficiency-letter output, exit codes 0/1/2.
- Agent skill in `skills/coi-lint/SKILL.md`.
