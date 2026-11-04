# Memory — coi-lint (handoff)

**What:** offline Python CLI that lints certificates of insurance (COIs, JSON or PDF) against YAML requirements → pass/warn/fail/waived findings with a fix for each problem (COI001–COI010 + YAML rule packs); `renewals` (30/60/90-day windows, .ics, renewal letters); `report` (md/html/csv/json); `watch-inbox` (IMAP → draft replies, never sends). CodeRabbit-style automation with zero AI/API cost.
**Who:** GC compliance coordinators, agency CSRs, property managers, devs building insurance/construction agents.
**Why:** COI checks are manual PDF reading; gaps seen in Covera, Alloovium, Veltha, Qlo, Hesper AI, Redoubt (YC S26/F26). See PRD.md §2.

## Decisions
- Deterministic core, no LLM in the verdict path → reproducible, auditable.
- Normalised JSON model first, PDF extraction second → rules are testable without PDFs.
- Stdlib dataclasses + argparse; only PyYAML at runtime; PDF/OCR libs are optional extras.
- Free for everyone (v0.3.0): no AI or paid service in the core. Checks run locally or in free GitHub Actions; "chat" = user's own AI via SKILL.md.
- PDF extraction never guesses: unreadable → COI009 fail; OCR → COI010 verify warning. Layouts are YAML field maps.
- Rule packs are declarative only (7 check types) so sharing them is safe; pack ids can't start with COI.
- Waivers need an `until` date; expired waivers are flagged on the finding.
- Exit codes 0 compliant / 1 deficient / 2 input error → CI-friendly.
- Fictional data only; never bundle copyrighted certificate forms; letters are drafts.
- Renewals (v0.2.0, from LinkedIn feedback by someone in compliance): reminder windows fixed at 90/60/30 days; .ics leaves out already-expired policies and uses stable UIDs so re-imports update events.

## Status
- **Done:** docs set; Phase 0 scaffold (model, 8 rules, text/json/letter output, examples, 4 tests passing); launch video, social cut and cover in docs/media; agent skill in skills/coi-lint/SKILL.md; v0.1.0 release; v0.2.0 renewals; v0.3.0 PDF extract (forms/text/OCR), fixes + explain, waivers, rule packs, extends/overrides, project report (md/html/csv/json), inbox watcher, Slack, JSON Schemas, CI, GitHub Action, pre-commit (39 tests).
- **In progress:** —
- **Next:** make the repo public; field maps for real certificate layouts (fictional values); labelled extraction-accuracy set.
- **Backlog:** configurable reminder windows, integrity signals, extraction timeouts, PyPI, MCP/tool wrapper, more rule packs.

## Open questions
- Which real-world certificate layouts to map first (needs fictional sample PDFs)?
- Support non-US certificate formats (e.g. AU public liability certificates)?
- Ship requirement templates per contract type, or leave to users?

## Docs
[PRD](PRD.md) · [Architecture](Architecture.md) · [Rules](Rules.md) · [Phases](Phases.md) · [Design](Design.md) · [CHANGELOG](CHANGELOG.md) · [README](README.md)

Run: `pip install -e ".[dev,pdf,ocr]" && pytest -q && coi-lint check examples/pdfs/northside-flat.pdf --rules examples/requirements.yaml --waivers examples/waivers.yaml`
