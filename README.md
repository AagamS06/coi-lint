# coi-lint

**Linting for certificates of insurance.** Check a COI against your project's requirements in one command: holder, limits, additional insured, waiver of subrogation, project wording and expiry — with a deficiency letter drafted for you.

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-F5B83D)
![Status](https://img.shields.io/badge/status-Phase%200-8A96A3)
![Tests](https://img.shields.io/badge/tests-pytest-3FB97A)

## Launch video

[![coi-lint launch video](docs/media/brag.jpg)](docs/media/brag.mp4)

20-second launch video: [docs/media/brag.mp4](docs/media/brag.mp4) (opens with a 5.4 s "rotate your phone" intro) · original cut: [docs/media/brag-original.mp4](docs/media/brag-original.mp4). YouTube link coming soon.

## The problem

Before a subcontractor, vendor or tenant can start work, someone has to collect their certificate of insurance and check it by eye against the contract: right certificate holder? limits high enough? additional insured and waiver of subrogation marked? project named? anything expiring next week? It's mechanical work done from PDFs, tracked in spreadsheets and chased by email — and the same problems bounce between general contractors, insureds and their brokers.

coi-lint makes those checks **deterministic, explainable and instant**. It helps:

- **Compliance coordinators** at general contractors and property managers who check dozens of COIs per project.
- **Insurance agency CSRs** who issue certificates and want to catch problems before they bounce back.
- **Developers building insurance/construction agents** who need a reliable verdict their agent can call, not a guess.

The gaps it targets were observed in public descriptions of YC Summer/Fall 2026 companies working on agency servicing, construction compliance, claims and underwriting — see [PRD.md §2](PRD.md#2-gaps-this-project-addresses-observed-in-yc-summer-2026-and-fall-2026-companies). Independent student project; not affiliated with any company mentioned.

## Features

| | Feature | Status |
|---|---|---|
| ✅ | Requirements profile in YAML (holder, minimum limits, AI/WOS, wording, warning window) | Phase 0 |
| ✅ | 8 rules with stable ids (COI001–COI008), pass / warn / fail | Phase 0 |
| ✅ | Terminal report, JSON output, deficiency-letter draft | Phase 0 |
| ✅ | CI-friendly exit codes (0 compliant, 1 deficient, 2 bad input) | Phase 0 |
| 🗺️ | Read certificate PDFs (form fields + text fallback) | Planned — Phase 1 |
| 🗺️ | Folder sweep, CSV register, `.ics` expiry calendar | Planned — Phase 1 |
| 🗺️ | PDF integrity signals, HTML report | Planned — Phase 2 |
| 🗺️ | PyPI package, agent tool wrapper | Planned — Phase 3 |

## Example

```console
$ coi-lint check examples/cert_sample.json --rules examples/requirements.yaml --today 2026-10-29
coi-lint · Northside Electric Co (fictional) → Harbor St Fit-out — subcontractor minimums

  ✓ COI001  Holder is Example Builders LLC
  ✓ COI003  General liability: in force until 2027-03-01
  ✓ COI005  General liability: each occurrence $1,000,000
  ✓ COI005  General liability: general aggregate $2,000,000
  ✓ COI006  General liability: additional insured marked
  ✗ COI007  General liability: waiver of subrogation NOT marked
  ! COI004  Automobile liability: expires in 17 days (2026-11-15)
  ✓ COI005  Automobile liability: combined single limit $1,000,000
  ✓ COI003  Umbrella / excess: in force until 2027-03-01
  ✗ COI005  Umbrella / excess: each occurrence $2,000,000 < required $5,000,000
  ✓ COI003  Workers' compensation: in force until 2027-01-01
  ✓ COI005  Workers' compensation: el each accident $1,000,000
  ✓ COI007  Workers' compensation: waiver of subrogation marked
  ✓ COI008  Description mentions 'Harbor St'

DEFICIENT  (2 fail, 1 warn, 11 pass)
```

Add `--format letter` for a deficiency request to the broker, or `--format json` for agents and CI.

## Tech stack

Python 3.10+ · PyYAML · stdlib dataclasses + argparse · pytest · ruff. Phase 1 adds pypdf and pdfplumber. No network calls, no LLM in the verdict path. Details in [Architecture.md](Architecture.md).

## Getting started

```bash
git clone https://github.com/AagamS06/coi-lint.git
cd coi-lint
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
coi-lint check examples/cert_sample.json --rules examples/requirements.yaml --today 2026-10-29
```

Write your own `requirements.yaml` (copy the example) and a normalised certificate JSON. PDF input arrives in Phase 1.

## Project structure

```
src/coi_lint/   cli.py · models.py · rules.py · report.py
examples/       requirements.yaml · cert_sample.json (fictional)
tests/          test_rules.py
docs/media/     launch video + poster
```

## Roadmap

Phase 0 (rules core) is done. Next: real PDFs and folder sweeps, then integrity signals and an HTML report, then PyPI and an agent tool wrapper. Full checklist in [Phases.md](Phases.md).

## Docs

| Doc | What's in it |
|-----|--------------|
| [PRD.md](PRD.md) | Problem, gaps (with sources), users, stories, features, metrics |
| [Architecture.md](Architecture.md) | Flow diagram, modules, data model, rules table, APIs |
| [Rules.md](Rules.md) | Contributor and AI-contributor rules, conventions, testing, security |
| [Phases.md](Phases.md) | Phased plan with checkboxes and exit criteria |
| [Design.md](Design.md) | Colours, themes, typography, components, accessibility |
| [Memory.md](Memory.md) | One-page handoff: decisions, status, next steps |

## Contributing

Issues and PRs welcome — especially requirement templates and (fictional) test certificates. Read [Rules.md](Rules.md) first: every rule needs a test, use fictional data only, and never commit real certificates.

## Licence

[MIT](LICENSE) © 2026 Aagam Shah
