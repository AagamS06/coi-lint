---
name: coi-lint
description: Check a certificate of insurance (COI) against a project's insurance requirements with the coi-lint CLI, explain every finding, draft a deficiency letter, and track upcoming renewals across many certificates (expiry list, calendar reminders, renewal-request drafts). Use when someone shares a COI or its details and asks whether it meets a contract, subcontract, lease or vendor agreement, which policies are expiring or need chasing, or what to ask the broker to fix.
---

# coi-lint

coi-lint is an offline, deterministic Python CLI. It compares one certificate of insurance with a requirements profile and returns pass / warn / fail findings with stable rule ids (COI001 to COI008), plus an optional deficiency-letter draft. Same inputs always give the same output, so treat its verdict as the source of truth instead of reasoning about limits yourself.

## 1. Install (once)

```bash
pip install "git+https://github.com/AagamS06/coi-lint.git"
coi-lint --version
```

Python 3.10+ is required. If the command isn't found, run `python -m coi_lint` instead of `coi-lint`.

## 2. Build the two inputs

**Requirements (YAML).** Ask the user for the contract's insurance clause, or copy `examples/requirements.yaml` from the repo and edit it. Money values are whole dollars.

```yaml
name: <project or contract name>
holder: <party that must be named as certificate holder>
warn_days: 30                       # warn when a policy expires within this many days
description_must_mention: [<project name or address>]
coverages:
  - kind: general_liability          # general_liability | auto | umbrella | workers_comp | <custom>
    min_limits: {each_occurrence: 1000000, general_aggregate: 2000000}
    additional_insured: true
    waiver_of_subrogation: true
  - kind: auto
    min_limits: {combined_single_limit: 1000000}
  - kind: umbrella
    min_limits: {each_occurrence: 5000000}
  - kind: workers_comp
    min_limits: {el_each_accident: 1000000}
    waiver_of_subrogation: true
```

**Certificate (JSON).** PDF input isn't built yet (it's on the roadmap), so read the certificate yourself and write the normalised JSON. Use the exact shape of `examples/cert_sample.json`: `insured`, `producer`, `holder`, `issued`, `description`, and `coverages[]` with `kind`, `policy_number`, `effective`, `expires` (YYYY-MM-DD), `limits`, `additional_insured`, `waiver_of_subrogation`.

- Copy values exactly as printed. If a field is unreadable or missing, leave it out rather than guess; the tool will then report it as missing.
- Show the user the JSON you extracted and ask them to confirm it before you rely on the verdict.

## 3. Run it

```bash
coi-lint check cert.json --rules requirements.yaml                  # human-readable report
coi-lint check cert.json --rules requirements.yaml --format json    # for parsing
coi-lint check cert.json --rules requirements.yaml --format letter  # deficiency-letter draft
```

Add `--today YYYY-MM-DD` to make a run reproducible. Exit codes: `0` compliant, `1` deficient, `2` bad input (fix the file named in the error and rerun).

JSON output contract:

```json
{"insured": "...", "requirements": "...", "verdict": "DEFICIENT | COMPLIANT_WITH_WARNINGS | COMPLIANT",
 "findings": [{"rule": "COI005", "severity": "fail", "coverage": "umbrella", "message": "..."}]}
```

## 3b. Track renewals across many certificates

Keep one certificate JSON per insured in a folder (e.g. `certs/`), then:

```bash
coi-lint renewals certs/                                    # expired + expiring in the next 90 days, soonest first
coi-lint renewals certs/ --within 30                        # tighter window
coi-lint renewals certs/ --rules requirements.yaml          # only the coverages the contract requires
coi-lint renewals certs/ --ics renewals.ics                 # calendar file: every upcoming expiry, reminders 90/60/30 days before
coi-lint renewals certs/ --format letter                    # one renewal-request draft per broker
coi-lint renewals certs/ --format json                      # {"today","within_days","renewals":[{insured, producer, coverage, policy_number, expires, days_left, window, source}]}
```

Paths can be files and/or folders (searched recursively). `window` is `expired`, `30`, `60`, `90` or `later`. Exit codes: `0` nothing expired, `1` at least one shown policy has already expired, `2` bad input. Suggest the `.ics` file when the user wants to stop chasing renewals by hand: importing it into their calendar gives them reminders 90, 60 and 30 days before each expiry. Re-importing an updated file updates events (stable UIDs) instead of duplicating them.

## 4. Explain the result

For `check`: lead with the verdict, then list the failures first, then the warnings. Quote each finding's message and rule id. For `renewals`: lead with anything expired, then the 30-day window, then the rest, and offer the calendar export and broker drafts.

| Rule | Meaning |
|------|---------|
| COI001 | Certificate holder doesn't match the requesting party |
| COI002 | A required coverage is missing from the certificate |
| COI003 | Policy expired (fail) / in force (pass) |
| COI004 | Policy expires within `warn_days`, or isn't effective yet (warn) |
| COI005 | A limit is below the required minimum, or missing |
| COI006 | Additional insured not marked |
| COI007 | Waiver of subrogation not marked |
| COI008 | Description of operations doesn't mention the required wording |

## 5. Boundaries

- coi-lint checks the user's own requirements. It doesn't judge whether coverage is *adequate*. Don't give insurance or legal advice; suggest confirming with their broker or contract manager.
- Letters (deficiency and renewal requests) are drafts. Never send them on the user's behalf without their explicit go-ahead.
- Certificates contain business and personal data. Keep them local, and don't commit real certificates to any repo.
