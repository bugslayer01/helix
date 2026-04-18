# Recourse — Loans-First Production Design

**Status:** Draft for implementation
**Date:** 2026-04-19
**Owner:** Helix team
**Target:** Hackathon submission + post-hackathon pilot

---

## 1. Problem Statement

Automated systems deny loans, flag job applications, and moderate content — with no mechanism for users to meaningfully contest the decision. The hackathon brief asks us to design a structured contestation interface that allows affected individuals to submit counter-evidence, forces the model to re-evaluate under the new information, and produces an explainable delta — showing exactly what changed and whether the decision flipped or held.

This design focuses on one vertical (loans) end-to-end, and establishes the shared architecture that makes future verticals (hiring, content moderation, admissions, fraud) a matter of training a new model and writing doc extraction prompts — not re-architecting the product.

---

## 2. Goals

1. **Brief-complete.** Ship a structured contestation interface that accepts counter-evidence, re-runs the same model, and produces an explainable delta with a flipped/held verdict.
2. **Not a gimmick.** Every load-bearing claim in the demo is backed by real code: real XGBoost, real SHAP, real PDF extraction, real cryptographic audit chain.
3. **Production-defensible.** A technically literate judge should be unable to identify a failure mode the product handwaves. Honest gaps are disclosed in the README, not hidden.
4. **Customer story.** The integration contract with a customer ("bring your own model") must be visible and reviewable, not implied.
5. **Fraud-resistant.** Evidence uploads must survive a deliberate attempt to tamper, replay, or fabricate. Ten-layer validation pipeline ("Evidence Shield").
6. **Domain-expandable.** Adding a new vertical after loans is ~4 days of model + prompt + seed data work. No re-architecture.
7. **One command to demo.** `make dev` brings up the full system. No wifi required once GLM-OCR is pulled.

## 3. Non-Goals

1. Training a novel credit-risk model. We use Kaggle's "Give Me Some Credit" feature set and synthetic data.
2. Building production identity (SSO, magic-link OTP). JWT + DOB 2FA stands in.
3. Multi-tenant isolation. Single-tenant SQLite; Postgres + RLS is an explicit post-hackathon upgrade path.
4. Court-grade document forensics. The Evidence Shield catches common fraud vectors, not nation-state tampering.
5. Full coverage of all four additional verticals. Adapters remain in-repo to prove the abstraction, but only loans is demo-ready.

---

## 4. Glossary

| Term | Meaning |
|---|---|
| **LenderCo** | Dummy customer system. Originates the rejected loan decision. |
| **Recourse** | Our product. Operates the contestation pipeline. |
| **Applicant** | End user; same person applies at LenderCo and contests at Recourse. |
| **Case** | One contestable decision. LenderCo calls it an `application`; Recourse calls it a `contest_case`. |
| **Intake doc** | Document uploaded at application time (bank statement, payslip). |
| **Evidence** | Document uploaded during contest to challenge a specific feature value. |
| **Proposal** | A validated feature override (old value → new value) that feeds the re-evaluation. |
| **Verdict** | Final decision after re-evaluation. Either `flipped` (outcome changed) or `held` (outcome stayed). |
| **Evidence Shield** | The 10-check validator applied to every evidence upload. |
| **Handoff** | The transition of an applicant from LenderCo's rejection page to Recourse's contest portal. |
| **Delta** | Per-feature before/after comparison with SHAP contribution diff. |

---

## 5. Architecture

### 5.1 Topology

Four processes, two logical systems, one shared scoring artifact.

```
┌──────────────────────────┐           ┌──────────────────────────┐
│  LenderCo (customer)     │           │  Recourse (our product)  │
├──────────────────────────┤           ├──────────────────────────┤
│ frontend :5174 (Vite)    │           │ frontend :5173 (Vite)    │
│ backend  :8001 (FastAPI) │◄─ 3 HTTP ─┤ backend  :8000 (FastAPI) │
│ lender.db                │   calls + │ recourse.db              │
│ uploads/ (intake docs)   │   1 webhook uploads/ (evidence)      │
└──────────────┬───────────┘           └────────┬─────────────────┘
               │                                │
               └───── shared/ package ──────────┘
                 adapters/loans.py + trained model artifact
                 ocr/ (GLM-OCR client + pdfplumber)
                 validators/ (Evidence Shield)
                 jwt_utils.py
                         │
                         └── Ollama :11434 (glm-ocr:bf16)
                             local, non-quantized, 2.2 GB
```

**Design principles:**

- **Two separate databases.** LenderCo never reads Recourse's DB; Recourse never reads LenderCo's. All cross-boundary communication is HTTP.
- **One shared model artifact.** Both services load the same serialized XGBoost model via `shared.adapters.loans`. SHA-256 of the artifact is stored in every case record on both sides; drift aborts re-eval with HTTP 409.
- **All AI runs locally.** GLM-OCR via Ollama. Zero external API calls on the hot path. Data sovereignty story holds: no applicant document ever leaves the server.
- **Single repo, multiple services.** Simplifies dev; `make dev` brings up everything. Services are independently deployable (each has its own `main.py`, DB, uploads dir).

### 5.2 Repo Layout

```
helix/
├── BUILD_BRIEF.md
├── README.md                   # hackathon pitch + run instructions
├── Makefile
├── docs/
│   ├── ARCHITECTURE.md
│   └── superpowers/specs/
│       └── 2026-04-19-recourse-loans-production-design.md
├── scripts/
│   ├── dev.py                  # one-command runner
│   ├── seed.py                 # loads demo cases
│   ├── reset.py                # wipes and reseeds
│   ├── smoke.py                # end-to-end round-trip test
│   └── seed/
│       └── loans/
│           ├── priya_sharma.json
│           └── docs/
│               ├── payslip_current.pdf
│               ├── bank_statement_march.pdf
│               └── credit_report.pdf
├── shared/
│   ├── adapters/
│   │   ├── base.py             # DomainAdapter Protocol
│   │   └── loans.py            # XGBoost adapter
│   ├── models/
│   │   ├── loans artifact + SHAP explainer (existing)
│   │   ├── metadata/loans.json
│   │   ├── metadata/loans_hints.json
│   │   └── train_loans.py
│   ├── ocr/
│   │   ├── extract.py          # GLM-OCR client
│   │   ├── templates.py        # pdfplumber fast path
│   │   └── router.py           # chooses fast path vs GLM-OCR
│   ├── validators/
│   │   ├── shield.py           # orchestrator, runs all 10 checks
│   │   ├── doc_type.py
│   │   ├── freshness.py
│   │   ├── bounds.py
│   │   ├── cross_doc.py
│   │   ├── issuer.py
│   │   ├── format.py
│   │   ├── baseline.py
│   │   ├── metadata.py
│   │   ├── tamper.py
│   │   └── replay.py
│   └── jwt_utils.py            # sign/verify + webhook HMAC
├── customer-portal/
│   ├── backend/
│   │   ├── main.py             # FastAPI :8001
│   │   ├── routes/
│   │   │   ├── applications.py
│   │   │   ├── cases.py
│   │   │   ├── webhooks.py
│   │   │   └── operator.py
│   │   ├── services/
│   │   │   ├── intake.py
│   │   │   └── scorer.py
│   │   ├── db.py               # sqlite connection + schema init
│   │   ├── lender.db
│   │   └── uploads/
│   └── frontend/
│       ├── index.html
│       ├── package.json
│       ├── tailwind.config.js
│       └── src/
│           ├── App.tsx
│           ├── store.ts
│           ├── lib/api.ts
│           └── components/
│               ├── ApplyView.tsx
│               ├── StatusView.tsx
│               ├── DecisionView.tsx
│               └── OperatorView.tsx
├── backend/                    # existing Recourse backend, rewired
│   ├── main.py
│   ├── routes/
│   │   ├── handoff.py          # JWT exchange + session
│   │   ├── contest.py          # state machine
│   │   ├── evidence.py         # upload + Evidence Shield
│   │   ├── audit.py            # chain dump + verify
│   │   ├── operator.py         # ops console
│   │   └── review.py           # human-review path
│   ├── services/
│   │   ├── handoff.py
│   │   ├── rerun.py
│   │   ├── webhook_dispatcher.py
│   │   ├── audit_log.py
│   │   └── evidence_pipeline.py
│   ├── db.py
│   ├── recourse.db
│   └── uploads/
└── frontend/                   # existing Recourse frontend, patched
    └── src/
        ├── App.tsx
        ├── components/
        │   ├── HandoffView.tsx
        │   ├── CorrectionForm.tsx
        │   ├── EvidenceShieldPanel.tsx
        │   ├── OutcomeView.tsx
        │   └── ...
        └── lib/api.ts
```

---

## 6. Data Model

All SQLite, WAL mode, foreign keys enforced. Two databases.

### 6.1 `customer-portal/lender.db`

```sql
CREATE TABLE applicants (
  id              TEXT PRIMARY KEY,
  full_name       TEXT NOT NULL,
  dob             TEXT NOT NULL,                  -- ISO 8601
  email           TEXT NOT NULL,
  phone           TEXT,
  created_at      INTEGER NOT NULL
);

CREATE TABLE applications (
  id              TEXT PRIMARY KEY,
  applicant_id    TEXT NOT NULL REFERENCES applicants(id),
  amount          INTEGER NOT NULL,
  purpose         TEXT,
  status          TEXT NOT NULL CHECK (status IN ('intake','under_review','decided','in_contest','closed')),
  submitted_at    INTEGER NOT NULL,
  decided_at      INTEGER
);

CREATE TABLE intake_documents (
  id              TEXT PRIMARY KEY,
  application_id  TEXT NOT NULL REFERENCES applications(id),
  doc_type        TEXT NOT NULL,
  original_name   TEXT NOT NULL,
  stored_path     TEXT NOT NULL,
  sha256          TEXT NOT NULL,
  extracted_json  TEXT,
  uploaded_at     INTEGER NOT NULL
);

CREATE TABLE scored_features (
  application_id  TEXT PRIMARY KEY REFERENCES applications(id),
  feature_vector  TEXT NOT NULL,
  model_version   TEXT NOT NULL,
  scored_at       INTEGER NOT NULL
);

CREATE TABLE decisions (
  id              TEXT PRIMARY KEY,
  application_id  TEXT NOT NULL REFERENCES applications(id),
  verdict         TEXT NOT NULL CHECK (verdict IN ('approved','denied')),
  prob_bad        REAL NOT NULL,
  shap_json       TEXT NOT NULL,
  top_reasons     TEXT NOT NULL,
  source          TEXT NOT NULL CHECK (source IN ('initial','recourse_webhook')),
  decided_at      INTEGER NOT NULL
);

CREATE TABLE contest_handoffs (
  jti             TEXT PRIMARY KEY,
  application_id  TEXT NOT NULL REFERENCES applications(id),
  issued_at       INTEGER NOT NULL,
  expires_at      INTEGER NOT NULL,
  revoked_at      INTEGER
);
```

### 6.2 `backend/recourse.db`

```sql
CREATE TABLE contest_cases (
  id                 TEXT PRIMARY KEY,
  customer_id        TEXT NOT NULL,                -- 'lenderco' today; multi-tenant key later
  external_case_id   TEXT NOT NULL,
  external_ref       TEXT NOT NULL,
  applicant_display  TEXT NOT NULL,
  applicant_dob_hash TEXT NOT NULL,                -- sha256(dob || case_salt)
  snapshot_features  TEXT NOT NULL,
  snapshot_decision  TEXT NOT NULL,
  snapshot_shap      TEXT NOT NULL,
  model_version      TEXT NOT NULL,
  status             TEXT NOT NULL CHECK (status IN (
                       'open','evidence_review','re_evaluating',
                       'verdict_held','verdict_flipped','closed','revoked'
                     )),
  created_at         INTEGER NOT NULL,
  closed_at          INTEGER,
  UNIQUE (customer_id, external_case_id)
);

CREATE TABLE sessions (
  id              TEXT PRIMARY KEY,
  case_id         TEXT NOT NULL REFERENCES contest_cases(id),
  jti             TEXT NOT NULL,
  created_at      INTEGER NOT NULL,
  expires_at      INTEGER NOT NULL
);

CREATE TABLE used_jti (
  jti             TEXT PRIMARY KEY,
  consumed_at     INTEGER NOT NULL
);

CREATE TABLE evidence (
  id              TEXT PRIMARY KEY,
  case_id         TEXT NOT NULL REFERENCES contest_cases(id),
  target_feature  TEXT NOT NULL,
  doc_type        TEXT,
  stored_path     TEXT NOT NULL,
  sha256          TEXT NOT NULL,
  extracted_json  TEXT,
  extracted_value REAL,
  uploaded_at     INTEGER NOT NULL
);

CREATE TABLE evidence_validations (
  evidence_id     TEXT PRIMARY KEY REFERENCES evidence(id),
  checks_json     TEXT NOT NULL,
  overall         TEXT NOT NULL CHECK (overall IN ('accepted','flagged','rejected')),
  summary         TEXT NOT NULL,
  validated_at    INTEGER NOT NULL
);

CREATE TABLE proposals (
  id              TEXT PRIMARY KEY,
  case_id         TEXT NOT NULL REFERENCES contest_cases(id),
  feature         TEXT NOT NULL,
  original_value  REAL NOT NULL,
  proposed_value  REAL NOT NULL,
  evidence_id     TEXT REFERENCES evidence(id),
  status          TEXT NOT NULL CHECK (status IN ('validated','applied','rejected')),
  created_at      INTEGER NOT NULL
);

CREATE TABLE verdict_webhooks (
  id              TEXT PRIMARY KEY,
  case_id         TEXT NOT NULL REFERENCES contest_cases(id),
  new_decision    TEXT NOT NULL,
  new_prob_bad    REAL NOT NULL,
  new_features    TEXT NOT NULL,
  delta_json      TEXT NOT NULL,
  delivered_at    INTEGER,
  attempts        INTEGER NOT NULL DEFAULT 0,
  last_error      TEXT
);

CREATE TABLE audit_log (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id         TEXT NOT NULL,
  action          TEXT NOT NULL,
  payload_json    TEXT NOT NULL,
  prev_hash       TEXT NOT NULL,
  hash            TEXT NOT NULL,
  created_at      INTEGER NOT NULL
);

CREATE TABLE evidence_hash_index (
  sha256          TEXT PRIMARY KEY,
  first_seen_at   INTEGER NOT NULL,
  first_case_id   TEXT NOT NULL,
  seen_count      INTEGER NOT NULL DEFAULT 1
);
```

**Invariants enforced by code (not schema):**

- `contest_cases.model_version` must equal the live `shared.adapters.loans` model version at case creation AND at re-evaluation. Mismatch raises `ModelDrift` and returns HTTP 409.
- `audit_log.prev_hash` equals previous row's `hash`. Chain verification endpoint re-computes every row's hash and asserts equality.
- `snapshot_features` is immutable after case creation. All mutations land in `proposals`.
- Applicant DOB is never stored plaintext in `recourse.db`. Only `sha256(dob_iso || case_salt)` is stored.

---

## 7. API Contract

All endpoints return JSON unless noted. 4xx/5xx responses have shape `{ "error": { "code": "...", "message": "...", "hint": "..." } }`.

### 7.1 Cross-boundary (LenderCo ↔ Recourse)

Exactly three HTTP calls + one webhook. Nothing else crosses.

**Handoff (browser-carried JWT, no server call).** LenderCo mints a JWT and redirects the applicant to `http://localhost:5173/contest?t=<JWT>`. JWT payload:

```json
{
  "iss": "lenderco",
  "sub": "APP-A4F2-9E31",
  "case_id": "LN-2026-A4F2",
  "decision": "denied",
  "issued_at": 1712345678,
  "exp": 1712432078,
  "jti": "uuid4-single-use"
}
```

Signing: HS256 with shared secret `HELIX_JWT_SECRET`.

**Case fetch (Recourse → LenderCo).**

```
GET http://localhost:8001/api/v1/cases/{case_id}
Authorization: Bearer <same JWT>

200 OK →
{
  "case_id": "LN-2026-A4F2",
  "applicant": { "display_name": "Priya Sharma", "dob_hash": "sha256:..." },
  "decision": { "verdict": "denied", "prob_bad": 0.68, "decided_at": 1712345000 },
  "features": { "MonthlyIncome": 48000, "DebtRatio": 0.42, ... },
  "shap": [{ "feature": "...", "contribution": -0.14 }, ...],
  "top_reasons": ["Credit card use at 68%", ...],
  "model_version": "sha256:abc123...",
  "intake_docs": [{ "doc_type": "payslip", "uploaded_at": ... }]
}

401  bad/expired JWT
403  case revoked
404  unknown case
409  JWT case_id ≠ URL case_id
```

**Verdict webhook (Recourse → LenderCo).**

```
POST http://localhost:8001/api/v1/recourse/verdicts
Authorization: Bearer <HMAC of body with HELIX_WEBHOOK_SECRET>
Idempotency-Key: <verdict_webhook_id>

{
  "case_id": "LN-2026-A4F2",
  "outcome": "flipped",
  "new_decision": { "verdict": "approved", "prob_bad": 0.31 },
  "new_features": { "MonthlyIncome": 68000, ... },
  "delta": [
    { "feature": "MonthlyIncome", "old": 48000, "new": 68000, "evidence_id": "ev_..." }
  ],
  "audit_chain_head": "sha256:deadbeef...",
  "evidence_manifest": [
    { "id": "ev_...", "sha256": "...", "doc_type": "payslip", "overall": "accepted" }
  ],
  "model_version": "sha256:abc123..."
}

200 OK   persisted
409      model_version mismatch
Retry:   exponential backoff, max 5 attempts, 1h ceiling.
```

**Revoke (LenderCo → Recourse, optional).**

```
POST http://localhost:8000/api/v1/recourse/revoke
Authorization: Bearer <HMAC>
{ "case_id": "...", "reason": "applicant_withdrew" | "fraud_detected" | ... }
```

### 7.2 LenderCo internal (frontend → own backend)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/applications` | Start new application |
| POST | `/api/v1/applications/{id}/documents` | Upload intake doc |
| POST | `/api/v1/applications/{id}/submit` | Triggers OCR → scoring → decision |
| GET | `/api/v1/applications/{id}` | Poll status |
| GET | `/api/v1/applications/{id}/decision` | Get decision + top reasons |
| POST | `/api/v1/applications/{id}/request-contest-link` | Mint JWT, return contest URL |
| GET | `/api/v1/cases/{case_id}` | (Reused from 7.1) |
| POST | `/api/v1/recourse/verdicts` | (Accepts webhook from 7.1) |
| GET | `/api/v1/operator/cases` | Ops console — list |
| GET | `/api/v1/operator/cases/{id}` | Ops console — detail |
| GET | `/health` | Liveness |

### 7.3 Recourse internal (frontend → own backend)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/contest/session/preview` | Verify JWT only (no session issued); returns applicant display name + case summary for the handoff landing page |
| POST | `/api/v1/contest/open` | Exchange JWT + DOB for session |
| GET | `/api/v1/contest/session` | Current case state |
| GET | `/api/v1/contest/case` | Snapshot features/shap/reasons |
| POST | `/api/v1/contest/evidence` | Upload doc; runs Evidence Shield |
| DELETE | `/api/v1/contest/evidence/{id}` | Remove before submitting |
| POST | `/api/v1/contest/submit` | Finalize: re-eval + webhook dispatch |
| GET | `/api/v1/contest/outcome` | Verdict + delta |
| POST | `/api/v1/contest/request-review` | Path 3 — human reviewer escalation |
| GET | `/api/v1/operator/cases` | Recourse ops view |
| GET | `/api/v1/audit/{case_id}` | Dump full audit chain |
| GET | `/api/v1/audit/{case_id}/verify` | Re-hash chain, return ok/tampered |
| GET | `/health` | Liveness |

### 7.4 Security and auth

- **JWT signing.** HS256 with `HELIX_JWT_SECRET`. Shared between LenderCo and Recourse — in reality a per-customer secret rotated periodically. For demo, `.env` file.
- **Webhook HMAC.** `HELIX_WEBHOOK_SECRET`, separate from JWT secret. Request body hashed with HMAC-SHA256, hex result sent as `Authorization: Bearer`.
- **CORS.** LenderCo frontend whitelists `:8001` only. Recourse frontend whitelists `:8000` only. Cross-backend browser calls forbidden.
- **Session cookies.** HTTP-only, SameSite=Lax, 24h expiry. Bound to case id at issue time.
- **Rate limits.** 100 req/min per IP on public endpoints; stricter on `/contest/open` (10 req/min) and `/evidence` (20 req/min per session).
- **Audit logging.** Every state-changing endpoint writes one `audit_log` row before returning. Read-only endpoints do not log.

---

## 8. Flows

### 8.1 Happy path (full round-trip)

1. Priya opens LenderCo portal (`:5174`), creates application, uploads payslip + bank statement + credit report.
2. LenderCo backend runs GLM-OCR on each doc, extracts features, calls `shared.adapters.loans.LoansAdapter.predict()` → verdict = denied, prob_bad = 0.68.
3. LenderCo stores decision; frontend shows "Denied" with top 3 SHAP reasons and a "Contest this decision" button.
4. Priya clicks. LenderCo backend mints JWT, returns URL `http://localhost:5173/contest?t=<JWT>`.
5. Browser redirects. Recourse frontend reads `t` from URL, shows `HandoffView` with DOB field.
6. Priya enters DOB. Frontend POSTs `/contest/open` with `{token, dob}`.
7. Recourse backend:
   - Verifies JWT signature, exp, jti not in `used_jti`.
   - Calls `GET http://localhost:8001/api/v1/cases/{case_id}` with JWT.
   - Verifies `sha256(dob || case_salt)` matches LenderCo's `dob_hash`.
   - Creates `contest_cases` row (snapshot of features + decision + SHAP + model_version).
   - Marks `jti` consumed. Issues session cookie.
   - Writes `audit_log` row: `case_opened`.
8. Frontend displays SHAP bars; Priya sees `MonthlyIncome=48000` contributed strongly negative.
9. Priya navigates to CorrectionForm for `MonthlyIncome`, uploads `payslip_current.pdf`.
10. Frontend POSTs multipart to `/contest/evidence` with `{target_feature: "MonthlyIncome"}`.
11. Recourse backend:
    - Writes file to `backend/uploads/{case_id}/{uuid}.pdf`.
    - Computes SHA-256.
    - Routes to `shared.ocr.router.extract(path, expected_doc_type="payslip")`:
      - pdfplumber fast path extracts text layer. If digital PDF with parseable structure → return structured fields.
      - Else → send image to GLM-OCR with JSON schema prompt → parse response.
    - Feeds extraction + case snapshot into `shared.validators.shield.run(evidence, case)`:
      - Runs all 10 checks.
      - Returns `ValidationReport{ overall, checks[], summary }`.
    - Writes `evidence` + `evidence_validations` rows.
    - If `overall == accepted` → creates `proposals` row with `status=validated`, new `proposed_value`.
    - Writes `audit_log` row: `evidence_uploaded` + `validator_ran`.
    - Returns `{ evidence_id, extracted_value, validation_report }`.
12. Frontend shows `EvidenceShieldPanel` with 10-check breakdown.
13. Priya uploads one more doc (bank statement → drives down DebtRatio). Repeat step 11.
14. Priya clicks "Re-evaluate". Frontend POSTs `/contest/submit`.
15. Recourse backend:
    - Collects all `proposals` with `status=validated`, applies them to snapshot features → new feature vector.
    - Verifies `model_version` matches live model version.
    - Calls `shared.adapters.loans.LoansAdapter.predict(new_features)` → new verdict.
    - Computes delta: per-feature `old → new` + SHAP contribution diff.
    - Sets `contest_cases.status` = `verdict_flipped` or `verdict_held`.
    - Marks proposals `applied`.
    - Writes `verdict_webhooks` row.
    - Writes `audit_log` rows: `model_reran`, `verdict_computed`.
    - Returns outcome to frontend.
16. `webhook_dispatcher` background task POSTs to LenderCo `/api/v1/recourse/verdicts` with HMAC.
17. LenderCo verifies HMAC, persists new decision with `source=recourse_webhook`, closes application.
18. Recourse writes `audit_log` row: `webhook_delivered`.
19. Priya sees `OutcomeView`: outcome + delta + "Approved. Decision updated with LenderCo."

### 8.2 Replay attempt

JWT URL is forwarded to a different person. They click and are redirected to Recourse. `/contest/open` requires DOB. Attacker doesn't know Priya's DOB → fails 2FA → no session issued. `used_jti` entry is written only after DOB passes; attacker can retry but still needs DOB.

### 8.3 Model drift

Engineer retrains the model between case creation and re-evaluation. Live `MODEL_VERSION` changes. At re-eval, Recourse checks `contest_cases.model_version` against live `MODEL_VERSION` → mismatch → raises `ModelDrift`. Frontend shows "Model updated since you filed; your case is escalating to human review." Case status becomes `open` again with a `review_required` flag.

### 8.4 Fraud attempt — tampered payslip

Priya edits her payslip in Acrobat to claim ₹90k income (real: ₹48k). Uploads.

- `shared.ocr.router` sends to both pdfplumber and GLM-OCR.
- pdfplumber reads text layer → "Net Salary: 48,000" (internal).
- GLM-OCR reads rendered image → "Net Salary: 90,000" (edited visual).
- `validators.tamper.check()` compares → divergence > 10% → `{passed: false, severity: "high", detail: "Text layer and rendered content disagree"}`.
- Shield overall → `rejected`. No proposal created. `audit_log` gets `evidence_rejected` with details.
- Frontend shows red banner + explanation.

### 8.5 Revocation

LenderCo discovers fraud in a different channel. Calls `POST /api/v1/recourse/revoke {case_id, reason}`. Recourse sets `contest_cases.status = 'revoked'`. Any in-flight session returns 403 on next call. Audit log records the revocation.

---

## 9. Evidence Shield — The Ten Checks

Every evidence upload passes through all ten checks. Each returns:

```python
@dataclass
class CheckResult:
    passed: bool
    detail: str
    severity: Literal['low', 'medium', 'high']
```

Shield aggregate rule:

- Any `high` failure → overall `rejected`.
- Any `medium` failure → overall `flagged` (proposal allowed but marked for operator review).
- All passed or only `low` → overall `accepted`.

### 9.1 `doc_type_matches_claim`

Ensures the uploaded document actually describes the feature being contested. Uses GLM-OCR's classification head plus keyword heuristics on extracted text.

- Payslip for income correction → passes.
- Bank statement for income correction → passes (extractor computes income from deposits).
- Credit report for income correction → fails `high` ("Wrong document type").
- Random screenshot → fails `high`.

### 9.2 `freshness`

Reads document's issue date from extraction; compares to current date.

- Payslip: ≤ 90 days → pass; 90-180 → `low`; >180 → `high` ("Stale document").
- Bank statement: must cover at least one month in the last 120 days.
- Credit report: ≤ 30 days → pass; >30 → `medium`.

### 9.3 `bounds`

Extracted value must fall within `adapter._bounds_for(feature)`. Rejects obvious garbage (income `₹50,000,000/mo`, dependents `-3`).

### 9.4 `cross_doc_consistency`

If two or more evidence docs pertain to the same feature, their extracted values must agree within 5%. Two payslips saying ₹48k and ₹92k → `high` failure.

### 9.5 `issuer_present`

Looks for letterhead markers: employer name, bank name, logo region, PAN/GSTIN, signature block. GLM-OCR returns `issuer` field in schema; absence = `medium` failure ("Unattributed document").

### 9.6 `format_sanity`

Currency symbols present, dates parse, account numbers are masked (bank policy). Regex-based, no LLM needed.

### 9.7 `plausibility_vs_baseline`

New claim compared to prior LenderCo value. `MonthlyIncome` can change ≤ 3× realistically. 10× jump = `medium` ("Implausible delta — confirm with operator"). Tunable per-feature via `realistic_delta_multiplier` in adapter metadata.

### 9.8 `pdf_metadata_check`

Inspects PDF metadata (Creator, Producer, CreationDate, ModDate).

- PDF claims to be from 2024-03 but `CreationDate=2026-04` → `medium` ("Metadata suggests recent regeneration").
- Creator = "Canva" or "Microsoft Word" for a bank statement → `low` flag.
- ModDate > CreationDate + 24h → `medium` ("Recently modified").

### 9.9 `text_vs_render`

Compares `pdfplumber` text-layer output vs GLM-OCR visual read. Divergence in key numeric fields > 10% → `high` ("In-place edit detected").

### 9.10 `replay`

SHA-256 of upload queried against `evidence_hash_index`. Hit on a different case ID → `high` ("Document already used in another case").

---

## 10. Shared Module

### 10.1 Adapter Protocol (forward-compatible with future domains)

```python
class DomainAdapter(Protocol):
    domain_id: str
    display_name: str
    model_version_hash: str

    # Scoring
    def predict(self, features: dict) -> Prediction: ...
    def explain(self, features: dict) -> list[SHAPRow]: ...

    # Schema
    def feature_schema(self) -> list[FeatureSchema]: ...
    def profile_groups(self) -> list[ProfileGroup]: ...

    # Evidence expansion seams (new in this design)
    def intake_doc_types(self) -> list[DocTypeSpec]: ...
    def evidence_doc_types(self, target_feature: str) -> list[DocTypeSpec]: ...
    def extract_prompt(self, doc_type: str) -> ExtractPromptSpec: ...

    # Presentation
    def verbs(self) -> dict[str, str]: ...
    def path_reasons(self) -> dict[str, list]: ...
    def legal_citations(self) -> list[str]: ...
    def suggest_counterfactual(self, features: dict) -> list[dict]: ...
```

`DocTypeSpec` describes a document type: its ID, display name, accepted file formats, required freshness window, whether it's an image/scan vs digital PDF. `ExtractPromptSpec` gives GLM-OCR the JSON schema for structured output + a natural-language prompt.

**No domain string appears in shared orchestration code.** The validator, OCR router, JWT util, session manager, and webhook dispatcher all receive adapter-produced metadata and operate on it uniformly.

### 10.2 OCR router

```python
def extract(path: Path, expected_doc_type: str, adapter: DomainAdapter) -> ExtractionResult:
    spec = adapter.extract_prompt(expected_doc_type)
    # Fast path: pdfplumber template for known-digital PDFs
    if is_digital_pdf(path):
        result = templates.try_parse(path, spec)
        if result.confidence > 0.85:
            return result
    # Fallback: GLM-OCR via Ollama
    return glm_ocr.extract(path, spec)
```

### 10.3 JWT utilities

```python
sign_handoff(case_id, applicant_id, decision, ttl_hours=24) -> str
verify_handoff(token: str) -> HandoffClaims                  # raises on invalid/expired
sign_webhook_body(body: bytes) -> str                         # HMAC-SHA256 hex
verify_webhook_body(body: bytes, sig: str) -> None            # raises on mismatch
```

Secrets loaded from `.env`: `HELIX_JWT_SECRET`, `HELIX_WEBHOOK_SECRET`.

---

## 11. Contest State Machine

```
            ┌──────────┐
            │   open   │◄──── JWT+DOB exchanged, case snapshot fetched
            └────┬─────┘
                 │ evidence uploaded
                 ▼
         ┌─────────────────┐
         │ evidence_review │◄──── one or more proposals validated
         └────┬────────────┘
              │ /contest/submit
              ▼
         ┌─────────────────┐
         │  re_evaluating  │
         └─────┬───────────┘
               │ predict() returns
               ├─────────► outcome == old ──► verdict_held ──► webhook → closed
               └─────────► outcome != old ──► verdict_flipped ─► webhook → closed

    Alt transitions from any state:
    - revoke()          → revoked → closed
    - human-review path → review_pending → closed (no model re-run)
```

Transitions logged to `audit_log` with payload `{from, to, actor}`.

---

## 12. Audit Chain

Every state-changing action writes a row:

```python
def append(case_id, action, payload):
    prev_hash = last_hash_for_case(case_id)  # "0" * 64 for genesis
    ts = now()
    body = f"{prev_hash}|{case_id}|{ts}|{action}|{json.dumps(payload, sort_keys=True)}"
    h = sha256(body.encode()).hexdigest()
    insert(case_id, action, payload, prev_hash, h, ts)
```

Tracked actions:

| Action | When |
|---|---|
| `case_opened` | JWT+DOB exchange succeeds |
| `evidence_uploaded` | Multipart file written |
| `validator_ran` | Evidence Shield completes |
| `evidence_rejected` | Shield overall = rejected |
| `proposal_validated` | Shield overall = accepted; proposal created |
| `contest_submitted` | /contest/submit called |
| `model_reran` | adapter.predict returns new score |
| `verdict_computed` | outcome flipped/held determined |
| `webhook_dispatched` | Verdict POST sent |
| `webhook_delivered` | 200 ACK received |
| `webhook_failed` | Non-2xx after N retries |
| `case_revoked` | LenderCo revoke call |
| `review_requested` | Human-reviewer path taken |

### Verification

`GET /api/v1/audit/{case_id}/verify` re-reads all rows, re-computes each `hash` from `prev_hash + payload + ts + action + case_id`, compares to stored `hash`. Any mismatch → response `{ ok: false, broken_at_row: N }`. This takes <50 ms per case.

---

## 13. Frontend Architecture

### 13.1 LenderCo (customer-portal/frontend)

- **Stack:** Vite + React 19 + TypeScript + Tailwind + Zustand. Same tokens as Recourse for visual consistency (shared `tailwind.config.js` imported).
- **Views:**
  - `ApplyView` — multi-step intake form. Personal info → loan amount/purpose → doc uploads. Real `<input type="file">`.
  - `StatusView` — polls `/applications/{id}` every 2s until decided.
  - `DecisionView` — two branches:
    - Approved: "Congratulations. Funds will disburse within 2 business days."
    - Denied: SHAP top-3 reasons + "Contest this decision" button. Clicking calls `/request-contest-link` → redirects to JWT URL.
  - `OperatorView` — table of applications with filter/search. Click row → detail with full SHAP, audit summary, webhook delivery status. Mocks an internal LenderCo CS agent view.

### 13.2 Recourse (frontend)

- **Stack:** Existing. React 19 + Vite + Tailwind + Zustand + GSAP.
- **Changes:**
  - Remove `LoginView` (ref + DOB lookup). Replace with `HandoffView`:
    - On mount, read `t` query param. POST to `/contest/session/preview` (lightweight JWT verify) to get applicant display name and case summary.
    - Show DOB entry. Submit → `/contest/open` → session issued → navigate to contest step 1.
  - Replace seeded `DomainSelector` with a static loans view (domain switcher hidden behind `?dev=1` for the expansion pitch).
  - Add `EvidenceShieldPanel`: rendered alongside every uploaded evidence doc.
    ```
    Evidence Shield — 10/10 passed
      ✓ Document type matches claim
      ✓ Freshness (45 days old)
      ✓ Value within bounds
      ...
    ```
    Failed checks render red with the `detail` string. GSAP animates pass-by-pass to sell the forensics story.
  - Rewire `OutcomeView` to show:
    - Banner: "Your decision has changed." / "Your decision did not change."
    - Per-feature delta grid: old value | new value | SHAP contribution diff.
    - "Verdict sent to LenderCo at HH:MM on DATE."
    - Audit chain tail hash with "Verify" button → calls `/audit/{case_id}/verify`.

---

## 14. Testing Strategy

### 14.1 Unit tests

- `shared/validators/` — one test file per check, each exercises pass/low/medium/high cases.
- `shared/ocr/` — golden-file tests: input PDF → expected JSON. Includes one tampered PDF to verify `text_vs_render` catches it.
- `shared/jwt_utils.py` — sign/verify roundtrip, expired token, tampered signature.
- `shared/adapters/loans.py` — predict on known feature vectors matches stored SHAs (ensures model didn't drift in commits).

### 14.2 Integration

- `scripts/smoke.py` — end-to-end round-trip (happy path from §8.1). Runs against live `make dev` stack. Asserts:
  1. Application created, 3 intake docs accepted, decision = denied.
  2. JWT issued, exchanged for session (with DOB).
  3. Evidence uploaded, Evidence Shield all-pass.
  4. `/contest/submit` → verdict flipped.
  5. Webhook delivered to LenderCo; LenderCo has new decision with `source=recourse_webhook`.
  6. Audit chain verifies ok.

### 14.3 Manual demo rehearsal

Pre-recorded demo PDFs in `scripts/seed/loans/docs/`. `make reset && make dev` takes system to a clean state in <10 seconds.

---

## 15. Deployment

### 15.1 Dev

`make dev` runs `scripts/dev.py` which:

1. Preflight: checks `ollama` daemon + `glm-ocr:bf16` pulled + Python venv + frontend `node_modules`.
2. Spawns four processes with color-coded log prefixes:
   - `[lender-api]`, `[lender-web]`, `[recourse-api]`, `[recourse-web]`
3. Polls `/health` on both backends, Vite readiness on both frontends.
4. Prints banner with clickable URLs.
5. On Ctrl-C, SIGTERM all four children, drain logs, exit 0.

### 15.2 Post-hackathon production path

- **Database.** SQLite → Postgres. Add row-level security policies keyed on `customer_id`. Keep schema.
- **Object storage.** Local `uploads/` → S3 with KMS-encrypted-at-rest. PDFs never written to disk unencrypted in prod.
- **Secrets.** `.env` → Vault / AWS Secrets Manager.
- **OCR.** Ollama local → dedicated GPU node running vLLM for throughput; same model, same prompts.
- **Job queue.** Inline webhook dispatch → dedicated worker (Celery / Arq) with dead-letter queue.
- **Identity.** JWT + DOB → SSO (Okta) for enterprise; magic-link OTP for applicants.
- **Multi-tenancy.** `customer_id` already on every row. Add tenant-scoped API keys, RLS enforcement, per-tenant buckets.

---

## 16. Honest Gaps

Every demo product has them. Disclosing ours preempts judge probing.

1. **Single-tenant SQLite.** Section 15.2 addresses the upgrade path.
2. **No email infra.** JWT URL is shown to applicant directly in the UI instead of emailed. For demo clarity. Real deployment swaps in transactional email.
3. **Evidence Shield is heuristic, not forensic.** Checks 8 and 9 catch common fraud (tampering, regeneration) but could be defeated by a skilled forger. Appropriate threat model for Art. 22 compliance, not criminal investigation.
4. **GLM-OCR is 5 weeks old (March 2026).** Well-tested on common layouts; may misfire on edge-case docs. Mitigation: pdfplumber fast path for known templates + deterministic error handling.
5. **Only loans is full-depth.** Other 4 adapters remain in-repo as heuristic stubs to prove the expansion seams. Post-hackathon roadmap covers bringing each to full-depth in ~4 days.
6. **No rate limiting on demo.** Added in production path; local demo skipped for clarity.
7. **DOB 2FA is weaker than OTP.** Acknowledged; SSO/magic-link is the production upgrade.

---

## 17. Future-Domain Expansion

### 17.1 Seams baked into this design

These are the architectural decisions that make domain expansion ~4 days instead of ~4 weeks:

- `DomainAdapter.intake_doc_types()`, `evidence_doc_types(feature)`, `extract_prompt(doc_type)` — all extraction metadata owned by the adapter.
- No domain strings in shared orchestration.
- Template-driven frontend: customer portal and Recourse portal render intake forms and evidence forms dynamically from adapter schema.
- Seed data organized by domain: `scripts/seed/{domain}/`.
- Validator base is domain-agnostic; domain-specific rules live in the adapter's `extract_prompt` via schema constraints.

### 17.2 Per-domain cost breakdown

| Bucket | Cost | Covered by shared? |
|---|---|---|
| Infra + workflow (JWT, session, audit, webhook, state machine, DB schemas) | 0 days | Yes — built once |
| XGBoost model + feature schema + display copy + legal citations | ~2 days | No |
| Doc types + GLM-OCR prompts + domain validator rules | ~1-2 days | No |
| Demo PDFs + seed data | ~1 day | No |
| **Per-domain total** | **~4 days** | — |

### 17.3 Roadmap after loans

| Week | Milestone |
|---|---|
| Week 1 | Loans full depth + hackathon ship |
| Week 2 | Hiring adapter — train on Kaggle resume dataset; doc types = resume, LinkedIn export, recommendation letter |
| Week 3 | Content moderation adapter — heuristic scorer; doc types = moderation log, chat transcript, appeal form |
| Week 4 | Admissions adapter — GPA + test-score model; doc types = transcript, test score report |
| Ongoing | Fraud/KYC adapter — deprioritized until design partner identified |

---

## 18. Moat

In order from most defensible to most commoditized:

1. **Workflow infrastructure as a product.** A customer with their own model cannot ship GDPR Art. 22-compliant contestation in under 6-12 months. We sell that in 2 weeks: 3 endpoints + 1 webhook. This is the primary unassailable moat.
2. **Evidence Shield.** The 10-layer validator is harder to write than it looks. Every production fraud attempt we see across customers compounds our detection rules. Single-tenant builders cannot accumulate this signal.
3. **Tamper-evident audit chain.** SHA-256 linked log is a regulatory artifact, not just a feature. Customers get legal defense material out of the box.
4. **No data egress.** GLM-OCR local → applicant documents never leave the customer's infra boundary. Huge enterprise buying signal.
5. **Explainability UX.** Rendering SHAP well is a specialist craft; most ML teams are bad at it. We are the specialists for this specific job.
6. **Cross-customer fraud signal** (post-hackathon, privacy-preserving). Same fake-payslip template hits N customers → network-effect detection.
7. **Regulatory timing.** GDPR Art. 22(3), DPDP §11, FCRA §615, EU AI Act Art. 86 mandate contestation. Buying pressure is deadline-driven.

Pitch shape for a customer call:

> You already have the model. You don't have the Art. 22-compliant contestation layer. Wire three endpoints to us. Your applicant hits reject → sees our white-labeled flow → we validate evidence, call your model back with corrected features, return verdict. You keep custody of the model and the raw decision data. We custody evidence and the audit chain (30-day retention default). One signed contract, two weeks to pilot.

---

## 19. Demo Script

Target: 4 minutes for judges. Opens with the problem, closes with a live flipped verdict and an audit chain verification.

**(0:00–0:20) Hook.**
"Priya applied for a ₹5L loan at LenderCo. She was denied 30 seconds ago by an XGBoost model she's never seen. GDPR Article 22 says she has a right to contest. But no portal exists. That's the gap we built for."

**(0:20–1:10) LenderCo portal.**
Open `:5174`. Show the denied decision. Point out the three SHAP reasons. Click "Contest this decision."

**(1:10–1:40) Handoff.**
Browser redirects to `:5173`. Point at the URL: `?t=<JWT>`. "That's a signed token — LenderCo tells us who this applicant is, and we verify before we let them in." Enter DOB.

**(1:40–2:30) Evidence upload + Shield.**
Land on contest view. Show SHAP bars. Click "Correct credit card use." Upload a bank statement PDF. As it extracts, narrate: "We just sent this to our local OCR model. No data left the server." Evidence Shield animates check-by-check, 10/10 green. Click second upload: a payslip. Shield runs again. "Now watch — I'll upload a tampered payslip from my other window." Upload. Check 9 (`text_vs_render`) fires red. "Caught it."

**(2:30–3:00) Re-eval and delta.**
Remove the tampered file. Click "Re-evaluate." `OutcomeView` shows: "Your decision has changed." Delta table: Credit card use 68% → 38%, DebtRatio 42% → 29%. New verdict: Approved.

**(3:00–3:20) Webhook.**
Switch to LenderCo operator tab. Refresh. Show new decision row with `source=recourse_webhook`.

**(3:20–4:00) Audit chain.**
Back to Recourse. Click "Verify audit chain." Response: `ok: true, rows: 14`. "Every state transition in this contest is cryptographically chained. Break any row → break the chain → verify fails." Close with the moat slide: "Workflow + Shield + audit chain. That's what the customer buys."

---

## 20. Success Criteria

1. `make dev` brings up all four services with health checks green within 15 seconds (after first pull).
2. Smoke test runs to completion with `verdict == approved` and audit chain verified.
3. Evidence Shield correctly flags a deliberately tampered PDF as `rejected` with `text_vs_render` = high.
4. `/audit/{case_id}/verify` returns `ok: true` on all test cases.
5. Model drift (swapping the serialized model between case creation and re-eval) surfaces cleanly as HTTP 409 with a human-readable error.
6. README renders on GitHub without broken images/diagrams and can be skimmed in 3 minutes.

---

## 21. Implementation Sequence

Nine phases. Each ends in a clean commit that leaves the repo in a working state relative to what's been built so far.

1. Shared module (OCR + validators + JWT)
2. LenderCo backend
3. LenderCo frontend
4. Recourse backend rewire
5. Recourse frontend patches
6. One-command dev runner (`scripts/dev.py` + Makefile)
7. Seed data + demo PDFs
8. README + architecture doc
9. End-to-end smoke test

Detailed plan lives in the implementation plan document produced by the `writing-plans` skill after this spec is approved.

---

## Appendix A — Example JSON Payloads

### Case snapshot (Recourse → LenderCo response)

```json
{
  "case_id": "LN-2026-A4F2",
  "applicant": {
    "display_name": "Priya Sharma",
    "dob_hash": "sha256:8a6c..."
  },
  "decision": {
    "verdict": "denied",
    "prob_bad": 0.6812,
    "decided_at": 1712345000
  },
  "features": {
    "RevolvingUtilizationOfUnsecuredLines": 0.68,
    "DebtRatio": 0.42,
    "MonthlyIncome": 48000,
    "age": 34,
    "NumberOfOpenCreditLinesAndLoans": 4,
    "NumberOfTimes90DaysLate": 0,
    "NumberRealEstateLoansOrLines": 1,
    "NumberOfTime30-59DaysPastDueNotWorse": 0,
    "NumberOfTime60-89DaysPastDueNotWorse": 0,
    "NumberOfDependents": 2
  },
  "shap": [
    {"feature": "RevolvingUtilizationOfUnsecuredLines", "contribution": -0.141},
    {"feature": "DebtRatio", "contribution": -0.089},
    {"feature": "MonthlyIncome", "contribution": -0.062}
  ],
  "top_reasons": [
    "Credit card use at 68% (typical approvals under 30%)",
    "Debt-to-income ratio 42% (typical approvals under 31%)",
    "Monthly income ₹48,000 (typical approvals above ₹55,000)"
  ],
  "model_version": "sha256:a1b2c3d4e5f6...",
  "intake_docs": [
    {"doc_type": "payslip", "uploaded_at": 1712344980},
    {"doc_type": "bank_statement", "uploaded_at": 1712344985},
    {"doc_type": "credit_report", "uploaded_at": 1712344990}
  ]
}
```

### Evidence Shield report

```json
{
  "evidence_id": "ev_01HXZ...",
  "extracted_value": 68000,
  "overall": "accepted",
  "summary": "All 10 checks passed. Payslip verified against internal consistency and baseline.",
  "checks": [
    {"name": "doc_type_matches_claim", "passed": true, "severity": "low", "detail": "Classified as payslip; target feature = MonthlyIncome."},
    {"name": "freshness", "passed": true, "severity": "low", "detail": "Issued 2026-04-10 (9 days old)."},
    {"name": "bounds", "passed": true, "severity": "low", "detail": "68000 within [0, 10000000]."},
    {"name": "cross_doc_consistency", "passed": true, "severity": "low", "detail": "No conflicting evidence on file for this feature."},
    {"name": "issuer_present", "passed": true, "severity": "low", "detail": "Employer: Infosys Ltd. PAN visible."},
    {"name": "format_sanity", "passed": true, "severity": "low", "detail": "₹ symbol present; dates parsed."},
    {"name": "plausibility_vs_baseline", "passed": true, "severity": "low", "detail": "1.4× prior (48000 → 68000); within 3× multiplier."},
    {"name": "pdf_metadata_check", "passed": true, "severity": "low", "detail": "Creator: Adobe Acrobat; dates coherent."},
    {"name": "text_vs_render", "passed": true, "severity": "low", "detail": "Text layer and rendered OCR agree (68000)."},
    {"name": "replay", "passed": true, "severity": "low", "detail": "SHA-256 not seen in evidence_hash_index."}
  ]
}
```

### Verdict webhook body

```json
{
  "case_id": "LN-2026-A4F2",
  "outcome": "flipped",
  "new_decision": {"verdict": "approved", "prob_bad": 0.312},
  "new_features": {
    "RevolvingUtilizationOfUnsecuredLines": 0.38,
    "DebtRatio": 0.29,
    "MonthlyIncome": 68000,
    "age": 34,
    "NumberOfOpenCreditLinesAndLoans": 4,
    "NumberOfTimes90DaysLate": 0,
    "NumberRealEstateLoansOrLines": 1,
    "NumberOfTime30-59DaysPastDueNotWorse": 0,
    "NumberOfTime60-89DaysPastDueNotWorse": 0,
    "NumberOfDependents": 2
  },
  "delta": [
    {"feature": "MonthlyIncome", "old": 48000, "new": 68000, "evidence_id": "ev_01...", "contribution_old": -0.062, "contribution_new": 0.041},
    {"feature": "DebtRatio", "old": 0.42, "new": 0.29, "evidence_id": "ev_02...", "contribution_old": -0.089, "contribution_new": 0.017},
    {"feature": "RevolvingUtilizationOfUnsecuredLines", "old": 0.68, "new": 0.38, "evidence_id": "ev_03...", "contribution_old": -0.141, "contribution_new": 0.058}
  ],
  "audit_chain_head": "sha256:d4f8b2e9...",
  "evidence_manifest": [
    {"id": "ev_01...", "sha256": "a1...", "doc_type": "payslip", "overall": "accepted"},
    {"id": "ev_02...", "sha256": "b2...", "doc_type": "bank_statement", "overall": "accepted"},
    {"id": "ev_03...", "sha256": "c3...", "doc_type": "credit_report", "overall": "accepted"}
  ],
  "model_version": "sha256:a1b2c3d4e5f6..."
}
```

---

## Appendix B — Environment Variables

```
HELIX_JWT_SECRET=                # HS256 secret shared between LenderCo and Recourse
HELIX_WEBHOOK_SECRET=            # separate HMAC secret for webhook bodies
HELIX_OLLAMA_URL=http://localhost:11434
HELIX_OLLAMA_MODEL=glm-ocr:bf16
HELIX_LENDER_DB=customer-portal/backend/lender.db
HELIX_RECOURSE_DB=backend/recourse.db
HELIX_LENDER_UPLOADS=customer-portal/backend/uploads
HELIX_RECOURSE_UPLOADS=backend/uploads
HELIX_LENDER_BASE_URL=http://localhost:8001
HELIX_RECOURSE_BASE_URL=http://localhost:8000
HELIX_JWT_TTL_HOURS=24
HELIX_SESSION_TTL_HOURS=24
HELIX_WEBHOOK_MAX_ATTEMPTS=5
```

---

*End of design spec.*
