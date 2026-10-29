# Memory — coi-lint (handoff)

**What:** offline Python CLI that lints certificates of insurance (COIs) against a project's YAML requirements → pass/warn/fail findings (COI001–COI008), JSON, deficiency-letter draft.
**Who:** GC compliance coordinators, agency CSRs, property managers, devs building insurance/construction agents.
**Why:** COI checks are manual PDF reading; gaps seen in Covera, Alloovium, Veltha, Qlo, Hesper AI, Redoubt (YC S26/F26). See PRD.md §2.

## Decisions
- Deterministic core, no LLM in the verdict path → reproducible, auditable.
- Normalised JSON model first, PDF extraction second → rules are testable without PDFs.
- Stdlib dataclasses + argparse; only PyYAML at runtime.
- Exit codes 0 compliant / 1 deficient / 2 input error → CI-friendly.
- Fictional data only; never bundle copyrighted certificate forms; letters are drafts.

## Status
- **Done:** docs set; Phase 0 scaffold (model, 8 rules, text/json/letter output, examples, 4 tests passing); launch video, social cut and cover in docs/media; agent skill in skills/coi-lint/SKILL.md; v0.1.0 release.
- **In progress:** —
- **Next:** CI workflow; Phase 1 `extract/forms.py` (pypdf form fields).
- **Backlog:** text fallback, sweep + CSV, .ics export, integrity signals, HTML report, PyPI, agent tool wrapper.

## Open questions
- Best field map for flattened certificates without form fields?
- Support non-US certificate formats (e.g. AU public liability certificates)?
- Ship requirement templates per contract type, or leave to users?

## Docs
[PRD](PRD.md) · [Architecture](Architecture.md) · [Rules](Rules.md) · [Phases](Phases.md) · [Design](Design.md) · [README](README.md)

Run: `pip install -e .[dev] && pytest -q && coi-lint check examples/cert_sample.json --rules examples/requirements.yaml --today 2026-10-29`
