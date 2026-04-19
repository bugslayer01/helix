# Recourse

**A contestation-as-infrastructure product for B2B decision systems.**
Your customer owns their model. You plug in three HTTP endpoints + one webhook.
Their rejected applicants get a GDPR Art. 22(3)-compliant contest flow, a
forensic evidence-validation pipeline, and a tamper-evident audit chain —
without them having to build any of it.

Submitted for the **Model Decision Contestation Interface** brief.

---

## The brief (why we exist)

> Automated systems deny loans, flag job applications, and moderate content —
> with no mechanism for users to meaningfully contest the decision. Design a
> structured contestation interface that allows affected individuals to submit
> counter-evidence, forces the model to re-evaluate under the new information,
> and produces an explainable delta — showing exactly what changed and whether
> the decision flipped or held.

Brief asks three things. Recourse delivers all three plus the adapter seams
that make domains beyond loans a ~4-day effort per vertical instead of a
re-architecture.

| Brief requirement | How Recourse delivers |
|---|---|
| "Structured contestation interface for counter-evidence" | JWT handoff + DOB 2FA + **10-check Evidence Shield** on every upload |
| "Forces the model to re-evaluate under new information" | Same `shared.adapters.loans` model artifact re-run on patched feature vector, model-version SHA-256 pinned both sides |
| "Explainable delta — what changed, flipped or held" | Full before/after SHAP diff + per-feature delta table + flipped/held banner + webhook back to the customer |

---

## The moat (what we're actually selling)

In order from most defensible to most commoditized. The first three are
load-bearing for the B2B sales motion.

1. **Workflow infrastructure as a product.** A customer with their own model
   cannot ship an Art. 22-compliant contestation layer in under 6–12 months.
   Recourse ships that workflow: JWT handoff, evidence intake, validator,
   re-evaluation, audit chain, webhook. Three endpoints to wire up, two weeks
   to pilot.
2. **Evidence Shield.** Every upload passes through ten forensic checks:
   doc-type match, freshness, bounds, cross-doc consistency, issuer
   attribution, format hygiene, plausibility vs baseline, PDF metadata
   forensics, text-vs-render tamper detection, and replay detection.
   Fraudulent evidence has to defeat all ten simultaneously. Single-tenant
   builders can't accumulate this detection signal.
3. **Tamper-evident audit chain.** SHA-256 chained log of every case event.
   `GET /api/v1/audit/{case_id}/verify` re-hashes the whole chain in <50 ms
   and reports the first broken row. Legal-defense artifact out of the box.
4. **No data egress.** Document extraction uses
   **[GLM-OCR](https://huggingface.co/zai-org/GLM-OCR)** (0.9B multimodal, MIT
   licensed, top OmniDocBench v1.5 at 94.62) running locally via Ollama.
   Applicant documents never leave the customer's infrastructure boundary —
   the biggest enterprise buying signal on the table.
5. **Explainability UX.** SHAP bars, delta tables, before/after re-scoring
   panels. Rendering attribution well is a specialist craft; most ML teams
   are bad at it. We're the specialists for this specific job.
6. **Cross-customer fraud signal** (post-hackathon, privacy-preserving). Same
   fake-payslip template hits N customers → network-effect detection.
7. **Regulatory timing.** GDPR Art. 22(3), DPDP §11, FCRA §615, EU AI Act
   Art. 86, EU DSA Art. 17 all mandate contestation. Buying pressure is
   deadline-driven.

Pitch shape:

> "You already have the model. You don't have the Art. 22-compliant
> contestation layer. Wire three endpoints to us. Your applicant hits reject
> → sees our white-labeled flow → we validate evidence, re-run your model
> with corrected features, return the verdict. You keep custody of the model
> and the raw decision data. We custody evidence and the audit chain. One
> signed contract, two weeks to pilot."

---

## Architecture at a glance

```
┌──────────────────────────┐           ┌──────────────────────────┐
│  LenderCo (customer)     │           │  Recourse (our product)  │
├──────────────────────────┤           ├──────────────────────────┤
│ frontend :5174 (Vite)    │           │ frontend :5173 (Vite)    │
│ backend  :8001 (FastAPI) │◄─ 3 HTTP ─┤ backend  :8000 (FastAPI) │
│ lender.db (sqlite)       │   calls + │ recourse.db (sqlite)     │
│ uploads/ (intake docs)   │  1 webhook uploads/ (evidence)       │
└──────────────┬───────────┘           └────────┬─────────────────┘
               │                                │
               └────── shared/ package ─────────┘
                 adapters/loans.py + XGBoost artifact (pinned by SHA-256)
                 ocr/ (GLM-OCR client + pdfplumber fast path)
                 validators/ (Evidence Shield — 10 checks)
                 jwt_utils.py
                         │
                         └── Ollama :11434 (glm-ocr:bf16, local)
```

**Two completely separate databases. Zero shared tables.** The only thing the
two services share is the scoring code + model artifact, imported by both.
Cross-boundary communication is exactly three HTTP calls + one webhook,
documented under `docs/superpowers/specs/`.

---

## End-to-end flow

1. **Applicant submits at LenderCo** (`:5174`). Uploads payslip, bank
   statement, credit report. Each doc is extracted via `shared.ocr.router`
   (pdfplumber fast path → GLM-OCR fallback).
2. **LenderCo runs the XGBoost model.** Real prediction, real SHAP, real
   top-3 reasons. Denied decisions include a "Contest this decision" button.
3. **JWT handoff.** Clicking mints an HS256-signed token with
   `{case_id, applicant_id, decision, jti, exp}` and redirects the applicant
   to Recourse at `:5173/?t=<JWT>`.
4. **Recourse handoff page.** Verifies token signature + expiry via
   `/api/v1/contest/session/preview`, then asks for DOB. On submit,
   `/api/v1/contest/open` verifies the DOB hash against what LenderCo reports,
   exchanges the JWT for a session cookie, and single-uses the jti.
5. **Understand step.** Live SHAP bar chart, top reasons, model-version hash
   displayed to the applicant. This is the same artifact Recourse will re-run.
6. **Evidence upload + Shield.** For each contestable feature (monthly
   income, debt ratio, revolving utilization), the applicant uploads a doc.
   Each upload runs through `shared.validators.shield.run_shield` producing
   10 check results. Only `accepted` uploads produce proposals.
7. **Re-evaluation.** `/api/v1/contest/submit` applies validated proposals
   to the snapshot features, **re-verifies `model_version` hasn't drifted**
   (else HTTP 409), and calls `adapter.predict` on the new vector.
8. **Webhook back to LenderCo.** `services.webhook_dispatcher` posts the new
   verdict to `customer/api/v1/recourse/verdicts` with HMAC-SHA256 signature,
   Idempotency-Key, and up-to-5 exponential-backoff retries.
9. **Outcome view.** "Flipped" / "Held" banner + before/after delta table +
   one-click audit-chain verify button that re-computes every row's SHA-256.

---

## The Evidence Shield — 10 checks

Every evidence upload passes through all ten. Any `high` failure →
`rejected`. Any `medium` failure → `flagged` for operator review. All passed
or only `low` → `accepted` (proposal is created).

| # | Check | Catches |
|---|---|---|
| 1 | `doc_type_matches_claim` | Wrong doc type (credit report uploaded for income correction) |
| 2 | `freshness` | Stale docs (payslip from 2019 used in 2026) |
| 3 | `bounds` | Out-of-range (income ₹50M/mo) |
| 4 | `cross_doc_consistency` | Two uploaded docs contradict each other |
| 5 | `issuer_present` | No letterhead / employer / bank / PAN / signature block |
| 6 | `format_sanity` | Missing currency symbols, unparseable dates, unmasked account numbers |
| 7 | `plausibility_vs_baseline` | Income claim jumped 10× overnight |
| 8 | `pdf_metadata_check` | Created-in-Canva-yesterday for a "2019" payslip, ModDate > CreationDate by days |
| 9 | `text_vs_render` | Acrobat in-place edit: PDF text layer disagrees with rendered OCR |
| 10 | `replay` | SHA-256 already seen in a different case |

Cheat-resistance by layering, not magic. A forger has to beat every check
simultaneously. Hash catches replay; text-vs-render catches edits; metadata
catches regeneration; cross-doc catches inconsistency; baseline catches
implausibility. Defense in depth.

---

## Running it

### Prerequisites

- Python 3.12 (managed via `uv` or `mise`)
- Node 20+
- [Ollama](https://ollama.com/download) running locally
- The GLM-OCR model: `ollama pull glm-ocr:bf16` (~2.2 GB, one-time)

### First-time setup

```bash
# Python venv
uv venv --python 3.12 backend/.venv
uv pip install --python backend/.venv/bin/python -r backend/requirements.txt

# Frontend deps
make deps

# Ollama model (only once)
make model-pull
```

### Start everything (one command)

```bash
make dev
```

This runs `scripts/dev.py`, which:

1. Checks Ollama is running and GLM-OCR is pulled (starts daemon if not).
2. Verifies venv + `node_modules` are in place.
3. Spawns four subprocesses with color-coded log prefixes.
4. Polls `/health` on both backends until green.
5. Prints a banner with every URL the user needs.
6. Cleanly `SIGTERM`s everything on Ctrl-C.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HELIX / RECOURSE · All services online
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  recourse-api    http://localhost:8000/docs
  lender-api      http://localhost:8001/docs
  recourse-web    http://localhost:5173
  lender-web      http://localhost:5174
  ollama          http://localhost:11434
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Seed the demo case

```bash
make seed
```

Creates Priya Sharma's case in `lender.db`, attaches three intake PDFs
(payslip, bank statement, credit report), runs the XGBoost model against the
extracted feature vector, and persists a denied decision. Open `:5174` to
see it in the operator console.

### Other make targets

```bash
make reset        # wipe both DBs and uploads
make model-pull   # (re)pull glm-ocr:bf16
make smoke        # end-to-end round-trip test
```

---

## Demo script for judges (4 minutes)

1. **(0:00–0:20) Hook.** "Priya applied for a ₹5L loan at LenderCo. She was
   denied 30 seconds ago by an XGBoost model she's never seen. GDPR Art. 22
   says she has a right to contest. But no portal exists. That's the gap
   Recourse fills."
2. **(0:20–1:10) LenderCo portal (`:5174/?view=operator`).** Point at the
   decided application. Click through to the applicant's denial page. Point
   out the three SHAP reasons. Click "Contest this decision."
3. **(1:10–1:40) Handoff.** Browser redirects to `:5173/?t=<JWT>`. "That's
   the signed handoff token — LenderCo tells us who this applicant is, and
   we verify before we let them in." Enter DOB `1990-03-12`.
4. **(1:40–2:30) Evidence + Shield.** Land on the Understand step, show the
   SHAP bars. Go to Contest. Upload `scripts/seed/loans/docs/payslip_evidence_new.pdf`.
   Shield animates check-by-check, 10/10 green. Upload
   `credit_report_evidence_new.pdf`. Same. Then upload an edited payslip
   (mismatched text layer) and watch `text_vs_render` fire red.
5. **(2:30–3:00) Re-eval + delta.** Remove the tampered file. Click
   "Re-evaluate now." OutcomeView: "Your decision has changed." Delta table:
   Credit card use 68%→38%, Income ₹48k→₹68k. New verdict: Approved.
6. **(3:00–3:20) Webhook lands.** Switch to LenderCo operator tab. Refresh.
   New decision row appears with `source=recourse_webhook`.
7. **(3:20–4:00) Audit chain.** Back to Recourse. Click "Verify chain." The
   response returns `ok: true, rows: 14`. "Every state transition in this
   contest is cryptographically chained. Break any row → break the chain →
   verify fails." Close with the moat: "Workflow + Shield + audit chain.
   That's what the customer buys."

---

## Repository layout

```
helix/
├── BUILD_BRIEF.md                    # hackathon problem statement
├── README.md                         # you are here
├── Makefile                          # dev / seed / reset / smoke / model-pull / deps
├── docs/
│   └── superpowers/specs/
│       └── 2026-04-19-recourse-loans-production-design.md   # full spec
├── scripts/
│   ├── dev.py                        # one-command service orchestrator
│   ├── seed.py                       # Priya Sharma case + intake PDFs
│   ├── smoke.py                      # end-to-end round-trip assertion
│   └── seed/loans/docs/              # demo PDFs (gen_pdfs.py regenerates)
├── shared/                           # imported by both backends
│   ├── adapters/
│   │   ├── base.py                   # DomainAdapter Protocol (12 methods)
│   │   ├── loans.py                  # XGBoost + SHAP (the real one)
│   │   ├── _heuristic.py             # base for rule-based adapters
│   │   └── {hiring, moderation, admissions, fraud}.py  # stubs, kept to prove seams
│   ├── models/
│   │   ├── loans artifact            # trained XGBoost (SHA pinned both sides)
│   │   ├── SHAP TreeExplainer        # for live attribution
│   │   ├── metadata/loans.json       # contestability rules
│   │   ├── metadata/loans_hints.json # precomputed counterfactuals
│   │   └── train_loans.py            # reproducible training script
│   ├── ocr/
│   │   ├── extract.py                # GLM-OCR Ollama client
│   │   ├── templates.py              # pdfplumber fast path
│   │   └── router.py                 # "template first, model fallback"
│   ├── validators/                   # Evidence Shield (10 checks + orchestrator)
│   └── jwt_utils.py                  # sign/verify handoff + webhook HMAC
├── customer_portal/                  # "LenderCo" dummy customer
│   ├── backend/                      # FastAPI :8001
│   │   ├── routes/{applications, cases, operator, webhooks}.py
│   │   ├── services/{intake, scorer}.py
│   │   └── db.py                     # lender.db schema
│   └── frontend/                     # Vite :5174
│       └── src/components/{Intro,Form,Docs,Decision,Operator}View.tsx
├── backend/                          # Recourse
│   ├── routes/{handoff, evidence, contest, audit, operator, review}.py
│   ├── services/{handoff, evidence_pipeline, rerun, webhook_dispatcher, audit_log}.py
│   └── db.py                         # recourse.db schema
└── frontend/                         # Recourse :5173
    └── src/components/{Handoff,Understand,Contest,Review,Outcome}View.tsx
```

---

## What the model is doing

We use the public **[Give Me Some Credit](https://www.kaggle.com/c/GiveMeSomeCredit)**
feature set — 10 independently auditable financial signals. The model is an
XGBoost binary classifier (100 trees, depth 5) trained on 40k synthetic rows.

| # | Feature | Meaning |
|---|---|---|
| 1 | RevolvingUtilizationOfUnsecuredLines | Credit card balance / limit |
| 2 | age | Years |
| 3 | NumberOfTime30-59DaysPastDueNotWorse | Mild delinquencies (last 2 yr) |
| 4 | DebtRatio | Monthly debt / gross income |
| 5 | MonthlyIncome | Gross monthly in ₹ |
| 6 | NumberOfOpenCreditLinesAndLoans | Active lines |
| 7 | NumberOfTimes90DaysLate | 90+ day delinquencies |
| 8 | NumberRealEstateLoansOrLines | Mortgages/HELOCs |
| 9 | NumberOfTime60-89DaysPastDueNotWorse | Mid delinquencies |
| 10 | NumberOfDependents | People depending on you |

Decision rule: `approved = prob_bad < 0.5`. SHAP signs are flipped so
positive contribution = pushed toward approval.

Both sides of the pipeline — LenderCo's intake scoring and Recourse's
re-evaluation — load the shared model artifact via joblib and compare its
SHA-256 at every call. Drift raises HTTP 409.

---

## Regulatory grounding

Recourse is a contestation layer because automated decisions need them:

- **GDPR Article 22(3)** — right to contest and obtain human intervention.
- **EU AI Act Article 86** — right to explanation of individual decision-making.
- **India DPDP Act 2023, §11** — right to a human in the loop.
- **EU DSA Article 17** — content-removal statement of reasons + appeal.
- **US FCRA §615**, **EEOC Uniform Guidelines**, **NYC Local Law 144**.
- **CJEU *Dun & Bradstreet Austria* (Feb 2025)** — meaningful explanation of
  automated credit decisions.

Each domain adapter surfaces its own jurisdictional hooks to the UI.

---

## Honest gaps (disclosed)

Every demo product has them. Ours:

1. **Single-tenant SQLite.** Production upgrade is Postgres + row-level
   security on `customer_id`. Schema stays identical; wiring swap is
   a ~1 PR change.
2. **No email infra.** JWT URL is shown to the applicant directly in the UI
   instead of emailed. For demo clarity. Transactional email slots in
   cleanly behind `/applications/{id}/request-contest-link`.
3. **Evidence Shield is heuristic, not forensic-court grade.** Checks 8 and
   9 catch common fraud vectors (tampering, regeneration) but could be
   defeated by a skilled forger. Appropriate threat model for Art. 22
   compliance, not criminal investigation.
4. **GLM-OCR is 5 weeks old (March 2026).** Well-tested on common layouts;
   may misfire on edge-case documents. Mitigation: the pdfplumber template
   fast path handles every demo PDF in <50 ms without the model, and the
   router falls through to a template result if GLM fails.
5. **Only loans is full-depth.** Four other vertical adapters remain in-repo
   as heuristic stubs to prove the expansion seams, but the demo and pitch
   only promise loans.
6. **No rate limiting on demo.** Spec-ed at 100 req/min on public endpoints
   (20/min per session for evidence upload). Skipped for local clarity.
7. **DOB 2FA is weaker than magic-link OTP.** Acknowledged; SSO + OTP is
   the production upgrade path.

---

## Future-domain expansion

The adapter Protocol has three new seam methods:

- `intake_doc_types()` — what docs the customer portal accepts at application time.
- `evidence_doc_types(target_feature)` — what docs Recourse accepts to contest a specific feature.
- `extract_prompt(doc_type)` — the GLM-OCR JSON schema + prompt for this doc type in this domain.

**No domain strings exist in shared orchestration code.** The validator, OCR
router, JWT util, session manager, and webhook dispatcher all receive
adapter-produced metadata and operate on it uniformly.

Per-domain cost, assuming shared infra doesn't change:

| Bucket | Days | Who builds it |
|---|---|---|
| Infra (JWT, session, audit, webhook, DB schema, dev runner) | 0 | Shared, already built |
| Model + feature schema + adapter copy + legal citations | ~2 | Domain owner |
| Doc types + GLM-OCR prompts + domain validator rules | ~1-2 | Domain owner |
| Demo data + seed PDFs | ~1 | Domain owner |
| **Per-domain total** | **~4 days** | — |

Rough post-hackathon roadmap:

| Week | Vertical |
|---|---|
| +1 week | Hiring — Kaggle resume classifier + resume / LinkedIn export / recommendation letter doc prompts |
| +2 week | Content moderation — heuristic scorer + moderation log / chat transcript / appeal form |
| +3 week | Admissions — GPA + standardized-test model + transcript / test score report |
| Ongoing | Fraud / KYC — deprioritized until a design partner is identified |

---

## Design spec

The full design document is at
[`docs/superpowers/specs/2026-04-19-recourse-loans-production-design.md`](docs/superpowers/specs/2026-04-19-recourse-loans-production-design.md).
Sections cover: topology, data model, API contract, flows (happy path,
replay, model drift, tamper, revoke), the 10 Evidence Shield checks,
shared-module structure, state machine, audit chain verification, security
model, testing, deployment notes, honest gaps, expansion roadmap, and the
moat.

---

## License

MIT.
