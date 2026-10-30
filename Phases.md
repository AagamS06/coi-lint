# Phases — coi-lint

## Phase 0 — Setup and rules core
**Goal:** a working CLI that checks a normalised certificate against a requirements file.
- [x] Repo, MIT licence, docs set (PRD, Architecture, Rules, Phases, Design, Memory)
- [x] `pyproject.toml`, `src/` layout, `coi-lint` console script
- [x] Data model: `Certificate`, `Coverage`, `Requirements`
- [x] Rules COI001–COI008 + verdict
- [x] Text, JSON and deficiency-letter output; exit codes 0/1/2
- [x] Fictional examples (`examples/`) and pytest suite
- [ ] GitHub Actions: ruff + pytest on push

**Exit criteria:** `coi-lint check examples/cert_sample.json --rules examples/requirements.yaml` prints a report and all tests pass. ✅

## Phase 1 — MVP: real PDFs and sweeps
**Goal:** point it at a folder of certificate PDFs and get a register.
- [ ] `extract/forms.py`: read fillable form fields with pypdf, map to the model
- [ ] `extract/text.py`: text-layer fallback with a configurable field map
- [ ] Mark unreadable fields `unknown`; unknown required fields fail with "could not read"
- [ ] `coi-lint extract <pdf>` → JSON
- [x] `coi-lint renewals <files/dirs>`: expired + upcoming expiries across many certificates, 30/60/90-day windows (v0.2.0)
- [x] `--ics` expiry calendar export: one event per policy, reminders 90/60/30 days before (v0.2.0)
- [x] Renewal-request drafts grouped by broker (`renewals --format letter`) (v0.2.0)
- [ ] `coi-lint sweep <dir> --rules` → compliance table + CSV register
- [ ] 30 synthetic labelled certificates; extraction accuracy ≥ 95%

**Exit criteria:** a 100-file sweep runs in < 10 s with ≥ 95% field accuracy on the labelled set.

## Phase 2 — Hardening and trust
**Goal:** make results safe to rely on.
- [ ] Integrity signals: modified-after-issue, incremental saves, flattened fields, producer mismatch
- [ ] File size limits and extraction timeouts
- [ ] Static HTML report (uses Design.md tokens)
- [ ] Extra rules: primary & non-contributory, per-project aggregate, carrier rating field
- [ ] Property-based tests for limits and dates

**Exit criteria:** fuzzed PDFs never crash the tool; HTML report passes WCAG AA contrast.

## Phase 3 — Launch and integrations
**Goal:** easy for people and agents to adopt.
- [ ] Publish to PyPI
- [ ] Library docs + stable JSON schema file
- [ ] Tool/MCP wrapper so agents can call `check`
- [ ] Requirement templates folder (community contributions)
- [ ] Launch post + demo video (docs/media)

**Exit criteria:** `pip install coi-lint` works; at least one external contribution merged.
