# Phases — coi-lint

## Phase 0 — Setup and rules core
**Goal:** a working CLI that checks a normalised certificate against a requirements file.
- [x] Repo, MIT licence, docs set (PRD, Architecture, Rules, Phases, Design, Memory)
- [x] `pyproject.toml`, `src/` layout, `coi-lint` console script
- [x] Data model: `Certificate`, `Coverage`, `Requirements`
- [x] Rules COI001–COI008 + verdict
- [x] Text, JSON and deficiency-letter output; exit codes 0/1/2
- [x] Fictional examples (`examples/`) and pytest suite
- [x] GitHub Actions: ruff + pytest on push (v0.3.0, `.github/workflows/ci.yml`)

**Exit criteria:** `coi-lint check examples/cert_sample.json --rules examples/requirements.yaml` prints a report and all tests pass. ✅

## Phase 1 — MVP: real PDFs and sweeps
**Goal:** point it at a folder of certificate PDFs and get a register.
- [x] Read fillable form fields with pypdf, mapped by a YAML field map (v0.3.0, `extract.py`)
- [x] Text-layer fallback (pdfplumber + regexes) and OCR for scans (Tesseract) (v0.3.0)
- [x] Unreadable fields are never guessed: they fail as COI009; OCR'd certificates warn as COI010 (v0.3.0)
- [x] `coi-lint extract <pdf>` → JSON; `check`, `renewals` and `report` accept PDFs (v0.3.0)
- [x] `coi-lint renewals <files/dirs>`: expired + upcoming expiries across many certificates, 30/60/90-day windows (v0.2.0)
- [x] `--ics` expiry calendar export: one event per policy, reminders 90/60/30 days before (v0.2.0)
- [x] Renewal-request drafts grouped by broker (`renewals --format letter`) (v0.2.0)
- [x] Compliance sweep over a folder + CSV register: `coi-lint report --format csv` (v0.3.0)
- [ ] Field maps for common real-world certificate layouts (community; fictional values only)
- [ ] 30 synthetic labelled certificates; extraction accuracy ≥ 95%

**Exit criteria:** a 100-file sweep runs in < 10 s with ≥ 95% field accuracy on the labelled set.

## Phase 2 — Hardening and trust
**Goal:** make results safe to rely on.
- [ ] Integrity signals: modified-after-issue, incremental saves, flattened fields, producer mismatch
- [ ] Extraction timeouts
- [x] Static HTML report with Design.md tokens, light/dark (v0.3.0, `report --format html`)
- [x] Fix suggestion on every failing/warning finding; `coi-lint explain` (v0.3.0)
- [x] Waivers with required expiry dates; expired waivers flagged (v0.3.0)
- [x] File size and page limits on PDF input (v0.3.0)
- [ ] Extra rules: primary & non-contributory, per-project aggregate, carrier rating field
- [ ] Property-based tests for limits and dates

**Exit criteria:** fuzzed PDFs never crash the tool; HTML report passes WCAG AA contrast.

## Phase 3 — Launch and integrations
**Goal:** easy for people and agents to adopt.
- [ ] Publish to PyPI
- [x] JSON Schemas for certificates, requirements, waivers and packs (v0.3.0, `schemas/`)
- [x] GitHub Action, Pages workflow example, pre-commit hook, Slack webhook, inbox watcher (v0.3.0)
- [x] Rule packs (YAML) and `extends:` config inheritance (v0.3.0)
- [ ] Library docs
- [ ] Tool/MCP wrapper so agents can call `check`
- [ ] More rule packs / requirement templates (community contributions)
- [x] Launch post + demo video (docs/media)

**Exit criteria:** `pip install coi-lint` works; at least one external contribution merged.
