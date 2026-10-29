# PRD — coi-lint

> Linting for certificates of insurance. Paste in a COI and your requirements; get a pass/fail report, an expiry calendar and a ready-to-review deficiency letter.

## 1. Problem statement

Every time a subcontractor, vendor or tenant starts work, someone has to collect a **certificate of insurance (COI)** and check it by hand: is the right party named as certificate holder, are the limits high enough, is "additional insured" and "waiver of subrogation" marked, does it mention the project, and when does each policy expire? The work bounces between three people:

- the **requester** (general contractor, property manager, facilities team) who must check it,
- the **insured** (the subcontractor/vendor) who needs to produce it to get paid or start work,
- the **broker** (insurance agency CSR) who issues and re-issues it.

The checks are mechanical, but they are done by eye from PDFs, tracked in spreadsheets and chased by email. Expired or under-limit certificates slip through, and brokers get the same re-issue requests again and again.

## 2. Gaps this project addresses (observed in YC Summer 2026 and Fall 2026 companies)

Each gap is grounded in what the company publicly says on its YC page (viewed 29 Oct 2026). coi-lint is an independent project; none of these companies use, endorse or asked for it.

| # | Gap | Where it was observed | What coi-lint does |
|---|-----|-----------------------|--------------------|
| G1 | COIs are a recurring servicing chore for agency CSRs ("COIs and follow-ups drafted"), plus 90/60/30-day renewal reminders | **Covera** (F26) — AI operating system for independent P&C agencies | Deterministic pre-check so a CSR knows exactly what's wrong before re-issuing; expiry dates feed reminders |
| G2 | Builders need "compliance sweeps" over compliance records, registers and licences, with expiry alerts | **Alloovium** (S26) — document intelligence for construction | A rules file per project + a sweep over every subcontractor's certificate with expiry warnings |
| G3 | Work stalls on missing documents that must be chased by email/phone ("checks the file for missing documents", underwriters chasing "missing applications, loss runs") | **Veltha** (F26) — AI-native TPA; **Qlo** (S26) — AI underwriting agents | Missing coverages/limits become explicit findings, and the tool drafts the request letter |
| G4 | Documents may be tampered with; coverage has to be checked, not assumed | **Hesper AI** (F26) — P&C claims investigation agents ("detect tampered documents", "check coverage") | Phase 2: PDF integrity signals (edited-after-issue, flattened fields, incremental saves) shown next to the lint result |
| G5 | Small commercial insureds (contractors, trucking) constantly have to prove coverage to win and keep work | **Redoubt Insurance** (F26) — commercial insurance agency for contractors and trucking | Insureds/brokers can self-check a certificate against a GC's published requirements before sending it |

Shared root cause across all five: **coverage proof lives in semi-structured PDFs, and nobody has a cheap, open, deterministic checker.** AI agents in these products can call one instead of re-deriving the rules in a prompt.

## 3. Target users

1. **Project/compliance coordinator at a small general contractor** (primary) — checks 20–200 subcontractor COIs per project.
2. **Agency CSR / account manager** — issues COIs and wants to catch problems before the requester does.
3. **Property / facilities manager** — collects vendor and tenant COIs.
4. **Developers building insurance or construction agents** — want a library/CLI their agent can call for a deterministic verdict.

## 4. User stories

- As a coordinator, I write my project's insurance requirements once in YAML and run every certificate against it, so I stop re-reading the same spec.
- As a coordinator, I see which policies expire in the next 30 days across all subs, so nobody works uninsured.
- As a coordinator, I get a drafted deficiency letter listing exactly what to fix, so I can send it after a quick review.
- As a CSR, I lint a certificate against the requester's requirements before sending it, so it isn't bounced back.
- As a developer, I call `coi-lint check --format json` from my agent and get stable rule ids (COI001–COI008) I can act on.
- As a reviewer, I can see *why* a certificate failed (rule id + plain-English message), never a black-box score.

## 5. Core features

### MVP
- Requirements profile in YAML: holder, minimum limits per coverage, additional insured, waiver of subrogation, required project wording, warning window. ✅ (Phase 0)
- Normalised certificate JSON model + rules engine with 8 rules (COI001–COI008). ✅ (Phase 0)
- Output: coloured terminal report, JSON, deficiency letter draft. ✅ (Phase 0)
- PDF ingestion: read fillable-form fields from certificate PDFs; text-layer fallback with field mapping. (Phase 1)
- Folder sweep: `coi-lint sweep certs/ --rules project.yaml` → table of every insured + verdict. (Phase 1)
- Expiry calendar export (`.ics`) and CSV register. (Phase 1)

### Later
- PDF integrity signals (modification date after issue date, incremental-update count, producer mismatch). (Phase 2)
- Optional local web report (single static HTML page). (Phase 2)
- Library API + MCP/tool schema so agents can call it. (Phase 3)
- Requirement templates for common contract clauses (community-contributed). (Phase 3)

## 6. Non-goals

- Not an insurance advisor: it never says whether coverage is *adequate*, only whether it meets the requirements *you* wrote.
- Does not contact insurers or verify policies with carriers.
- Does not send emails; letters are drafts for a human.
- Does not ship or reproduce copyrighted industry forms.
- No cloud service, accounts or telemetry; certificates stay on the user's machine.

## 7. Success metrics

- Correctness: 100% of rule tests pass; every finding traceable to a rule id.
- Extraction (Phase 1): ≥ 95% field accuracy on a labelled set of 30 synthetic fillable certificates.
- Speed: a 100-certificate folder sweep in < 10 s on a laptop.
- Usefulness: a new user goes from `pip install` to a first report in < 5 minutes using the README.
- Adoption signals (honest, post-launch): GitHub stars/issues from real coordinators or CSRs; at least one external contributor adding a requirement template.
