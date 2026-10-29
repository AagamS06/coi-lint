# Rules — coi-lint

Rules for every contributor, human or AI.

## Do
- Keep the core deterministic: same certificate + same requirements + same `--today` → same output.
- Give every check a stable rule id (`COI###`) and a plain-English message that says what was found *and* what was expected.
- Write a test for every new rule and every bug fix (fail first, then fix).
- Use fictional data only in examples and tests (`(fictional)` in names, `0000` policy numbers).
- Keep functions small and pure; I/O lives in `cli.py` and `extract/`.

## Avoid
- Network calls in the core package.
- Making insurance-adequacy judgements ("you should buy more cover"). We check the user's requirements only.
- Sending emails or contacting brokers/carriers automatically.
- Copying or bundling copyrighted industry certificate forms.
- New dependencies without a reason written in the PR.

## Approved libraries
| Purpose | Library |
|---------|---------|
| Config | PyYAML |
| PDF form fields | pypdf |
| PDF text | pdfplumber |
| Tests | pytest |
| Lint/format | ruff |
Anything else: open an issue first.

## Coding conventions
- Python ≥ 3.10, type hints everywhere, `from __future__ import annotations`.
- `snake_case` functions, `PascalCase` dataclasses, constants in `UPPER_CASE`.
- Line length 120 (ruff). Docstring on every module.
- Money is stored as integer dollars; dates as `datetime.date`; never floats for limits.
- Commit messages: imperative, scoped — `rules: add COI009 primary/non-contributory`.

## Boundaries for AI contributors
- **May**: add rules + tests, improve messages, write extractors, update docs, fix bugs with a failing test.
- **May not**: change rule ids or JSON output keys (a breaking contract), weaken a test to make it pass, change the licence, or add telemetry.
- **Never** commit secrets, API keys, tokens or real certificates (`certs/` and `private/` are git-ignored).
- **Ask first** before destructive changes: deleting files, rewriting git history, renaming public modules, bumping the major version.
- Update `Memory.md` (Done / In progress / Next) at the end of each working session.

## Error-handling procedure
1. Bad input (missing file, malformed JSON/YAML, bad date) → clear one-line message on stderr, exit code `2`. No tracebacks for user errors.
2. Deficient certificate → report + exit `1` (useful in CI and scripts).
3. Unexpected exception → let it raise in development; open an issue with a minimal fictional reproduction.
4. Extraction uncertainty (Phase 1) → mark the field as `unknown`, never guess; unknown required fields become `fail` with "could not read".

## Testing expectations
- `python -m pytest -q` passes before every commit.
- Each rule has pass, fail and edge-case tests (boundary day for expiry, equal-to-minimum limits).
- Dates in tests are fixed via `today=`; no test depends on the real clock.
- Phase 1: a labelled set of synthetic certificates with expected JSON; accuracy is reported in CI.

## Security basics
- Certificates contain business and personal data: process locally, never upload.
- Parse YAML with `yaml.safe_load` only.
- Treat PDFs as untrusted input: no JavaScript execution, size limits on files, timeouts on extraction.
- Pin dependency minimums in `pyproject.toml`; review dependabot updates.
