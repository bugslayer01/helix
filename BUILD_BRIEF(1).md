# HackHelix T5 P3 — Build Brief

**Project codename:** Recourse
**Track:** T5 — Trustworthy AI & Responsible Systems
**Problem:** P3 — Model Decision Contestation Interface
**Domain:** Loan / credit decisions (locked — see §2)
**Build agent:** Claude Code
**Target:** Hackathon demo-grade, not production-grade. Every feature must survive a 3-minute live demo.

---

## 0. TL;DR for the builder

Build a web app where a user sees why they were denied a loan and is offered **three paths** to contest the decision: (1) correct existing information they believe was wrong, (2) submit new evidence, or (3) request human review without model re-run. Paths 1 and 2 run the *same classifier* on updated features and show an **animated visual delta** of how the decision shifted. Path 3 routes to a human reviewer and honors GDPR Article 22(3) / DPDP Section 11. Every step is logged to a tamper-evident audit trail. As a stretch, aggregate appeal patterns to surface model miscalibration to operators.

**What to optimise for in priority order:**
1. The waterfall animation landing cleanly (demo money shot)
2. Three-path contestation selector visible and legible
3. Structured evidence ingestion that visibly drives re-evaluation
4. Audit log visible in UI with SHA256 hashes
5. Legal framing in the README / demo intro
6. Institutional feedback loop (stretch only)

**What to never do:**
- Let an LLM make the decision. The LLM's *only* jobs are (a) plain-language translation of SHAP features, (b) suggesting evidence types. The classifier is a real sklearn / XGBoost model. Use **local Ollama** as primary with OpenAI as fallback — never let a live LLM call block the demo.
- Free-text appeal box as the primary contestation input. Structured form tied to contestable features.
- Pretty dashboards without a real model behind them.
- Pretend that re-running the model is always the right answer. Sometimes the user's complaint is about the model's appropriateness, not its inputs — that's Path 3's whole reason for existing.

---

## 1. The trap most teams will fall into (avoid)

> User types "I think this is wrong because..." → GPT-4 called with "reconsider this decision" → GPT outputs new verdict + explanation paragraph → UI shows before/after text.

This has no real model, no real interpretability, no real delta. Judges will have seen five of these by the time they reach us. If the build drifts toward this shape at any point, stop and reread this section.

---

## 2. Why loans (domain lock)

- **Public datasets exist and judges recognise them:** German Credit (UCI), Give Me Some Credit (Kaggle), LendingClub. Don't pick a dataset nobody's seen.
- **Features are intuitive:** income, debt-to-income, employment length, credit history length. Judges don't need a legend.
- **Evidence is real-world plausible:** pay stubs update income, employment letters update tenure, loan payoff receipts update DTI. Makes the "submit counter-evidence" flow legible in 30 seconds.
- **Legal tailwind is sharpest here:** Feb 2025 CJEU *Dun & Bradstreet Austria* ruling was literally a credit denial case. EU AI Act Article 86. India's DPDP Act. Open the pitch with these.
- **Stakes are legible without explanation:** "you were denied a loan" needs no setup.

Do not switch domain mid-build.

---

## 3. Architecture at a glance

```
┌──────────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                       │
│  ┌──────────────┐    ┌──────────────────────────────┐            │
│  │ Applicant    │ →  │ Path Selector                │            │
│  │ Profile View │    │ [Correct] [New Evidence] [Human] │        │
│  └──────────────┘    └────────────┬─────────────────┘            │
│                                   │                              │
│        ┌──────────────────────────┼──────────────────┐           │
│        ▼                          ▼                  ▼           │
│  ┌────────────┐          ┌────────────────┐   ┌────────────┐     │
│  │ Correction │          │ New Evidence   │   │ Human      │     │
│  │ Form       │          │ Upload Form    │   │ Review     │     │
│  └─────┬──────┘          └────────┬───────┘   │ Request    │     │
│        │                          │           └─────┬──────┘     │
│        └──────────┬───────────────┘                 │            │
│                   ▼                                 │            │
│        ┌──────────────────────┐                     │            │
│        │ Delta Waterfall View │                     │            │
│        │ (animated)           │                     │            │
│        └──────────┬───────────┘                     │            │
│                   │                                 │            │
│        ┌──────────┴─────────────────────────────────┘            │
│        ▼                                                         │
│  ┌──────────────┐    ┌────────────────┐                          │
│  │ Audit Log    │    │ Operator Panel │                          │
│  │ Panel        │    │ (stretch)      │                          │
│  └──────────────┘    └────────────────┘                          │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTP/JSON
┌──────────────────────────────┴───────────────────────────────────┐
│                  Backend (FastAPI + Python)                       │
│  ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐   │
│  │/evaluate │ │/contest │ │/review   │ │/audit  │ │/aggregate │   │
│  │          │ │(path 1+2)│ │(path 3) │ │        │ │           │   │
│  └────┬─────┘ └────┬────┘ └────┬─────┘ └───┬────┘ └─────┬─────┘   │
│       │            │            │           │            │        │
│  ┌────┴────────────┴───────┐ ┌──┴────────┐ ┌┴────────┐ ┌┴────────┐│
│  │ XGBoost + SHAP + DiCE   │ │ Human     │ │ SQLite  │ │ Pattern ││
│  │ classifier pipeline     │ │ review    │ │ audit   │ │ aggreg. ││
│  └────────────┬────────────┘ │ queue     │ │ log     │ └─────────┘│
│               │              └───────────┘ └─────────┘            │
│  ┌────────────┴────────────┐                                      │
│  │ LLM Helper               │                                      │
│  │ ┌──────────┐ ┌────────┐  │                                      │
│  │ │ Ollama   │→│ OpenAI │  │                                      │
│  │ │ (primary)│ │(fallbk)│  │                                      │
│  │ └────┬─────┘ └────────┘  │                                      │
│  │      └──→ static template│                                      │
│  │ ┌──────────────────────┐ │                                      │
│  │ │ Response cache (disk)│ │                                      │
│  │ └──────────────────────┘ │                                      │
│  └──────────────────────────┘                                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Tech stack (locked — do not substitute)

**Backend**
- Python 3.11+
- FastAPI + uvicorn
- scikit-learn, XGBoost (classifier)
- `shap` (feature attribution)
- `dice-ml` (counterfactual suggestions — "here's what would flip it")
- pandas, numpy
- SQLite via `sqlite3` stdlib (no ORM needed, it's a hack)
- `python-multipart` for file uploads
- `httpx` for async LLM calls
- `diskcache` for persistent LLM response caching

**LLM layer (scoped narrowly — see §4a)**
- **Primary:** Ollama running locally with `llama3.2:3b` or `qwen2.5:3b` (small, fast, reliable)
- **Fallback:** OpenAI API (gpt-4o-mini) if Ollama is unreachable or times out
- **Last resort:** Static template strings — never let the demo die because an LLM is slow

**Frontend**
- React 18 + Vite
- TypeScript (or JS if faster; consistency matters more than type safety here)
- Tailwind CSS
- Recharts for the waterfall + bars (has built-in animated transitions via `isAnimationActive` and `animationDuration`)
- Framer Motion for the chip flip and confidence counter tween (Recharts handles the bars; Framer Motion handles everything else)
- Zustand for state (lighter than Redux, faster to wire)

**Optional / stretch**
- Tesseract.js for OCR on uploaded pay stubs (pure frontend, no server call)
- OR: Claude API for extracting structured data from uploaded document images. Only if Tesseract is flaky.

**Do not use**
- No Next.js — Vite is faster to boot and we don't need SSR
- No Supabase / Firebase — SQLite file is enough, less auth friction
- No Docker for the demo — run locally, `npm run dev` + `uvicorn main:app --reload`
- No cloud-hosted LLM as *primary* — network flakiness will kill your demo

---

## 4a. LLM usage — narrow scope, hard rules

The LLM has **exactly two jobs** in Recourse. If the build drifts toward using the LLM for anything else, stop.

**Job 1: Plain-language translation of SHAP output.**
Input: `[{"feature": "DebtRatio", "value": 0.48, "contribution": -0.34}, ...]`
Output: "Your debt-to-income ratio was the primary factor. The model considered your existing debt obligations high relative to your income."
One call per evaluation. ~150 tokens out. Cache by SHAP-value-vector hash.

**Job 2: Evidence suggestion phrasing.**
Input: DiCE counterfactual `{"feature": "MonthlyIncome", "target": 72000}`
Output: "Upload a recent pay stub showing income above ₹72,000 to strengthen your case."
One call per contestation setup. ~80 tokens out. Cache by (feature, target_bucket) tuple.

**Hard rules:**
- The LLM **never** sees the decision logic. It sees SHAP output and generates text. That's it.
- The LLM **never** decides anything. No "should this be approved?" queries, ever.
- The LLM **never** interprets uploaded evidence. OCR + schema validation does that.
- All LLM calls are **async, non-blocking**. The decision and SHAP render immediately; the plain-language text pops in ~500ms later via a second render.
- **Timeout:** 2s on Ollama → retry once on OpenAI (3s timeout) → fall back to static template. Never stall the UI.
- **Pre-compute and cache** for the 3 seed applicants at startup. Live LLM calls only happen for the contestation paths, maybe 2-3 times per demo.

**Static template fallback (must always exist):**
```python
FALLBACK_REASON = "The top factor in this decision was {top_feature}. The model weighted this feature heavily compared to the others."
FALLBACK_EVIDENCE = "Consider providing updated documentation for {feature}, such as {evidence_type}."
```
Boring but never breaks. Ship this first, then layer the LLM on top.

---

## 5. Data and model

### Dataset
Primary: **Give Me Some Credit** (Kaggle) — binary classification (serious delinquency in 2 years), 150k rows, 10 features. Clean, well-known, features are legible.

Fallback: **German Credit** (UCI) if Kaggle download is slow — 1000 rows, 20 features, smaller but same shape.

### Features to use (Give Me Some Credit)
- `RevolvingUtilizationOfUnsecuredLines` (DTI-adjacent, contestable)
- `age` (NOT contestable — lock in UI)
- `NumberOfTime30-59DaysPastDueNotWorse` (contestable with payment records)
- `DebtRatio` (contestable)
- `MonthlyIncome` (contestable — this is the star of the demo)
- `NumberOfOpenCreditLinesAndLoans` (contestable)
- `NumberOfTimes90DaysLate` (contestable)
- `NumberRealEstateLoansOrLines` (contestable)
- `NumberOfTime60-89DaysPastDueNotWorse` (contestable)
- `NumberOfDependents` (NOT contestable — family structure)

### Contestability metadata
Maintain a static map: `{feature_name: {contestable: bool, evidence_type: str, reason: str}}`. The UI uses this to lock non-contestable fields and show the correct evidence upload affordance.

```python
CONTESTABILITY = {
  "MonthlyIncome": {
    "contestable": True,
    "evidence_type": "pay_stub",
    "reason": "Updatable with recent pay documentation"
  },
  "age": {
    "contestable": False,
    "evidence_type": None,
    "reason": "Protected attribute — not contestable"
  },
  # ...
}
```

### Model
- XGBoost classifier, 100 trees, max_depth=5. Train in a notebook, dump to `model.pkl` with joblib. Do not retrain on the fly.
- Accuracy target: whatever XGBoost gives out of the box with minimal tuning. This is not a Kaggle comp.
- Save: `model.pkl`, `feature_names.json`, `shap_explainer.pkl` (pre-fit TreeExplainer).

### SHAP integration
Use `shap.TreeExplainer` — fast, exact for tree models. Return per-feature contribution values with the prediction. This is the entire substrate of the delta visualisation.

### DiCE integration
Use `dice_ml.Dice` with method="random" (fastest) to generate 3 counterfactuals for denied applicants. These power the "you could try changing X" suggestions in the contestation form. Do not overthink DiCE config — defaults are fine for a demo.

---

## 6. API contract

All endpoints return JSON. All timestamps ISO 8601. All IDs UUID v4.

### `POST /evaluate`
Initial decision.
```json
Request:
{
  "applicant_id": "uuid",  // optional; generated if absent
  "features": {
    "MonthlyIncome": 4500,
    "DebtRatio": 0.42,
    "age": 34,
    ...
  }
}

Response:
{
  "case_id": "uuid",
  "decision": "denied" | "approved",
  "confidence": 0.73,
  "shap_values": [
    {"feature": "DebtRatio", "value": 0.42, "contribution": -0.34, "contestable": true},
    {"feature": "MonthlyIncome", "value": 4500, "contribution": -0.18, "contestable": true},
    ...
  ],
  "plain_language_reason": "Your debt ratio was the primary factor...",
  "suggested_evidence": [
    {"feature": "DebtRatio", "evidence_type": "loan_payoff_receipt", "target_value_hint": 0.28}
  ]
}
```

### `POST /contest`
Submit contestation — Path 1 (correct existing values) or Path 2 (add new evidence). Both re-run the classifier.
```json
Request:
{
  "case_id": "uuid",
  "contest_path": "correction" | "new_evidence",
  "reason_category": "stale_data" | "data_entry_error" | "circumstances_changed" | "missing_information",
  "user_context": "Optional short free text — goes to audit log, NOT to model",
  "updates": {
    "MonthlyIncome": 6200,    // new or corrected value
    "DebtRatio": 0.28
  },
  "evidence_refs": [
    {
      "feature": "MonthlyIncome",
      "evidence_type": "pay_stub",
      "filename": "paystub_march.pdf",
      "evidence_hash": "sha256:..."
    }
  ]
}

Response:
{
  "case_id": "uuid",
  "contest_path": "correction" | "new_evidence",
  "before": { decision, confidence, shap_values },
  "after":  { decision, confidence, shap_values },
  "delta": {
    "decision_flipped": true,
    "confidence_change": +0.41,
    "feature_deltas": [
      {
        "feature": "DebtRatio",
        "old_value": 0.42, "new_value": 0.28,
        "old_contribution": -0.34, "new_contribution": +0.12,
        "contribution_delta": +0.46
      }
    ]
  },
  "anomaly_flags": [],  // populated if an update exceeds realistic bounds
  "audit_entry_id": "uuid",
  "audit_hash": "sha256:..."
}
```

**Anomaly behaviour:** If a submitted update exceeds a realistic delta threshold (e.g., MonthlyIncome jumps >3x), populate `anomaly_flags` and route to human review instead of auto-returning the flipped decision. Demo can stub this — the plumbing matters more than the heuristic.

### `POST /review`
Path 3 — request human review without model re-run. Honors GDPR Article 22(3) and DPDP Section 11.
```json
Request:
{
  "case_id": "uuid",
  "review_reason": "protected_attribute_bias" | "inappropriate_use_of_model" | "model_misweighted_correct_data" | "other",
  "user_statement": "Free text — for the human reviewer, NOT the model",
  "max_length_chars": 2000
}

Response:
{
  "case_id": "uuid",
  "queue_position": 3,
  "estimated_review_window": "72 hours",
  "audit_entry_id": "uuid",
  "audit_hash": "sha256:...",
  "status": "queued_for_human_review"
}
```

**No model re-run on this endpoint.** Ever. The audit log explicitly records that the decision was queued for human review, not re-evaluated. This is the regulatory-compliance story.

### `GET /audit/{case_id}`
Full chronological log for a case — original decision, all contestation rounds, path taken per contest, every hash.

### `GET /aggregate` (stretch)
Returns patterns across all cases. Now segmented by path:
- "Path 1 (corrections) account for 62% of contests → data pipeline freshness issue"
- "Path 3 (human review) cites protected_attribute_bias in 18% of requests → audit recommended"
- "DebtRatio flipped 78% of Path 1+2 contests → threshold recalibration candidate"

---

## 7. Frontend components

### `ApplicantProfileView`
- Shows 10 feature values as a clean card
- "Evaluate" button → calls `/evaluate`
- On response: decision chip (red/green), confidence gauge, SHAP waterfall chart
- Contestable features visually distinguishable from locked ones (small lock icon on protected attributes)

### `PathSelector` — NEW
- Renders after initial denial, before any form
- Three large buttons, each with a short description:
  - **"Correct existing information"** — "I believe some of the data used was wrong" → routes to `CorrectionForm`
  - **"Submit new evidence"** — "I have updated documentation" → routes to `NewEvidenceForm`
  - **"Request human review"** — "I want a person to look at this decision" → routes to `HumanReviewForm`
- Each button shows a one-line legal/practical hint in muted text. The human-review button references GDPR Art 22(3) / DPDP Section 11 — don't hide the law, use it as a trust signal.
- Also requires a **reason category** dropdown (structured, not free-text) before any path proceeds. Populates the aggregate view.

### `CorrectionForm` (Path 1)
- Renders all current feature values as editable fields
- Each contestable field has a small "mark as incorrect" toggle — only flagged fields can be updated
- User enters the corrected value and selects evidence type from a fixed list (dropdown)
- Small DiCE hint — "Correcting DebtRatio to 0.30 or below would likely flip this decision"
- Submit calls `/contest` with `contest_path: "correction"`

### `NewEvidenceForm` (Path 2)
- Renders *only contestable* features as optional add-evidence fields
- Each field: "Upload new evidence" button → OCR extraction (stretch) or manual value entry (P0)
- Emphasis on "this is new information you didn't have at original application"
- Submit calls `/contest` with `contest_path: "new_evidence"`

### `HumanReviewForm` (Path 3)
- No feature inputs at all — this path does not touch the model
- Review-reason dropdown: `protected_attribute_bias` / `inappropriate_use_of_model` / `model_misweighted_correct_data` / `other`
- Free-text area (capped at 2000 chars) — "describe your concern for the human reviewer"
- Clear message above the form: "This submission will be reviewed by a human. The model will not re-evaluate your case automatically."
- Submit calls `/review` (not `/contest`)
- On success: shows queue position and estimated review window, writes audit entry

### `DeltaWaterfallView` ← THIS IS THE DEMO MONEY SHOT
(Renders only for Path 1 and Path 2 responses — Path 3 routes to `HumanReviewConfirmation` instead)
- Horizontal bar chart of SHAP contributions, one row per feature
- On contest submission: bars *animate* from old contribution to new contribution over 1.2s
- Bars that shifted sign (negative → positive or vice versa) animate through zero visibly
- Above the chart: decision chip that flips color/text synchronised with bar animation
- Above that: confidence number that tweens (e.g. 27% → 68%) in sync
- Below: summary — "4 features updated, decision changed from Denied to Approved, confidence +41%"

**Animation choreography (critical):**
```
t=0.0s: User clicks "Re-evaluate"
t=0.1s: API response received (backend should be <200ms)
t=0.2s: Bar animation starts, duration 1.0s, easeInOutCubic
t=0.6s: Decision chip flip begins (Framer Motion rotateY), duration 0.4s
t=0.8s: Confidence counter starts ticking (Framer Motion animate), duration 0.6s
t=1.4s: Everything settled, audit log entry fades in below
```
Do not let these fire simultaneously — the stagger is what makes it feel designed.

### `AuditLogPanel`
- Chronological list of events for current case
- Each row: timestamp, action, SHA256 hash of entry (truncated display, click to copy)
- Visible hash is worth a full point in the demo — looks like production-grade thinking

### `OperatorPanel` (stretch)
- Separate route `/operator`
- Shows aggregate: "Feature X has flipped 12/15 contests in last session"
- Chart: contest volume over time, flip rate per feature
- One-liner callout: "Model may be miscalibrated for low-income applicants — recommend threshold review"

---

## 8. The demo money shot — full script

90-second demo sequence. Rehearse this exact flow.

1. **(0:00–0:12)** Pitch opener. "In February 2025, the EU Court of Justice ruled that companies must provide meaningful explanations of automated credit decisions. India's DPDP Act Section 11 guarantees the right to human intervention. The EU AI Act Article 86 extends this further. No production system today lets a denied applicant meaningfully contest an automated decision. We built that — and we didn't just build one contestation path, we built three, because sometimes the model is right about the data but wrong to be used at all."

2. **(0:12–0:22)** Show applicant profile. Click Evaluate. Red "Denied" chip appears. SHAP waterfall renders — DebtRatio at -0.34 is the screaming red bar at the top. Plain-language reason appears below (from local Ollama): "Your debt-to-income ratio was the primary factor..."

3. **(0:22–0:32)** Click Contest. **Path selector appears with three options.** Narrate: "The user chooses the shape of their contest — correct wrong data, add new evidence, or escalate to a human. Each path triggers a different pipeline." Select "Correct existing information."

4. **(0:32–0:48)** Correction form. Flag DebtRatio as incorrect — "the existing loan was actually paid off but the credit bureau hadn't updated." Enter 0.28. Select evidence type: "loan payoff receipt." Call out the locked age and dependents fields — "protected attributes, system-enforced not contestable."

5. **(0:48–1:05)** Click Re-evaluate. **The money shot.** Bars animate — DebtRatio's red bar shrinks, crosses zero, becomes a green bar at +0.12. Decision chip flips red→green. Confidence number tweens 27% → 68%. Audit log entry fades in with SHA256 hash. Reason category ("stale_data") is visible in the audit row.

6. **(1:05–1:20)** Show Path 3 quickly. Reset to the original denial. Click "Request human review" this time. Select reason: "protected_attribute_bias." Show that *no model re-run happens* — submission goes to a queue with a timestamp and hash. Narrate: "This is the GDPR Article 22(3) path. Sometimes the user's complaint isn't about inputs — it's about the model itself being the wrong tool. We route those to humans, not back into the same black box."

7. **(1:20–1:30)** Operator view. "Across today's contests, 62% are corrections — our data pipeline has a freshness problem. 18% of human-review requests cite protected-attribute bias — audit recommended. DebtRatio flipped 78% of Path 1+2 contests — threshold recalibration candidate. This is the accountability layer that turns individual recourse into institutional feedback. Thank you."

---

## 9. File structure

```
recourse/
├── backend/
│   ├── main.py               # FastAPI app + route registration
│   ├── models/
│   │   ├── train.py          # One-shot training script
│   │   ├── model.pkl         # Committed artifact
│   │   ├── explainer.pkl     # Committed SHAP explainer
│   │   └── metadata.json     # Feature names + contestability map
│   ├── routes/
│   │   ├── evaluate.py
│   │   ├── contest.py         # Handles contest_path: correction | new_evidence
│   │   ├── review.py          # Path 3 — human review queue
│   │   ├── audit.py
│   │   └── aggregate.py
│   ├── services/
│   │   ├── classifier.py      # Wraps model + SHAP
│   │   ├── dice_service.py    # Wraps DiCE
│   │   ├── audit_log.py       # SQLite writer + hasher
│   │   ├── anomaly_check.py   # Realistic-delta bounds checker
│   │   ├── llm_helper.py      # Ollama primary → OpenAI fallback → template
│   │   └── llm_cache.py       # diskcache wrapper for LLM responses
│   ├── db/
│   │   ├── audit.db           # SQLite — gitignored
│   │   └── llm_cache/         # diskcache dir — gitignored
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ApplicantProfileView.tsx
│   │   │   ├── PathSelector.tsx              # NEW — the three-path fork
│   │   │   ├── CorrectionForm.tsx            # Path 1
│   │   │   ├── NewEvidenceForm.tsx           # Path 2
│   │   │   ├── HumanReviewForm.tsx           # Path 3
│   │   │   ├── HumanReviewConfirmation.tsx   # Path 3 success screen
│   │   │   ├── DeltaWaterfallView.tsx
│   │   │   ├── AuditLogPanel.tsx
│   │   │   └── OperatorPanel.tsx
│   │   ├── lib/
│   │   │   ├── api.ts          # Fetch wrappers
│   │   │   └── store.ts        # Zustand state
│   │   └── styles/
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── notebooks/
│   └── train_model.ipynb     # For reproducibility, not used at runtime
├── data/
│   └── cs-training.csv       # Give Me Some Credit — gitignored, download script
├── scripts/
│   └── download_data.sh
├── README.md                 # Pitch + legal framing + setup
└── .gitignore
```

---

## 10. Build phases

### P0 — must ship (aim: 60% of available time)
- Train model, save artifacts
- `/evaluate` endpoint returning decision + SHAP
- `/contest` endpoint accepting `contest_path` (correction or new_evidence), returning delta
- `/review` endpoint for Path 3 — writes audit entry, does NOT call model
- **`PathSelector` component** rendering the three-path fork
- `ApplicantProfileView`, `CorrectionForm`, `NewEvidenceForm`, `HumanReviewForm`, `DeltaWaterfallView`
- **Waterfall animation working cleanly** — this is non-negotiable
- Basic audit log (write to SQLite, show in UI, distinguishes path taken)
- Static-template LLM fallback (no live LLM needed for P0 — ship the templates first)
- Seed data: 3 pre-loaded applicant profiles for demo

### P1 — should ship (aim: next 25%)
- SHA256 hashing of audit entries, visible in UI
- DiCE counterfactual suggestions in the correction and new-evidence forms
- Ollama integration with async non-blocking calls for plain-language reasons
- Response caching via `diskcache` keyed on SHAP-vector hash
- OpenAI fallback wired in with 2s timeout on Ollama
- Locked feature indicators in UI (age, dependents)
- Polished styling (Tailwind, dark mode looks good in demo)

### P2 — stretch (remaining 15%)
- OCR-based evidence upload (Tesseract.js)
- Anomaly-check circuit breaker (realistic-delta bounds) that routes outliers to human review
- `OperatorPanel` with aggregate view segmented by contest path
- Multiple contestation rounds on same case
- Export audit trail as PDF

**Cut ruthlessly if time compresses.** The waterfall animation + three-path selector + audit log with hashes is the minimum viable *differentiator*. Everything else is garnish.

---

## 11. Judge attack surface (rehearse answers)

Likely questions. Have answers ready.

1. **"How is this different from DiCE / Alibi?"** — DiCE generates counterfactuals for ML engineers. We're an end-user contestation system with structured evidence intake, forced re-evaluation, audit trails, and delta visualisation. DiCE is a library; we are the product layer that makes it useful to the person whose loan was denied.

2. **"Couldn't you just use an LLM for all of this?"** — No. An LLM making the decision is exactly the problem we're solving. The model has to be the same classifier, re-run on updated features. The LLM is a thin translation layer, nothing more. Point at the code.

3. **"What stops someone from submitting fake evidence?"** — Demo answer: the audit trail with hashes means operators can spot-check and revoke approvals. Production answer: evidence is signed or verified against sources (e.g., payroll APIs). Demo doesn't implement this, spec acknowledges it.

4. **"Isn't this just a form with extra steps?"** — Walk them through the delta waterfall. Show the SHAP contribution change. Show the institutional aggregate panel. The form is 10% of the system.

5. **"Why should a company adopt this?"** — CJEU Dun & Bradstreet (Feb 2025), EU AI Act Article 86, DPDP Act 2023. Regulators are requiring meaningful explanation and contestation. This is the compliance layer.

6. **"Won't biased models just re-approve the same way?"** — The institutional feedback loop (OperatorPanel) is specifically designed to surface systematic bias in contest outcomes. If a feature flips 80% of contests for one population, the aggregator flags miscalibration. This *exposes* bias that unaudited models hide.

7. **"What about the explanation being wrong?"** — SHAP for tree models is exact, not approximate. TreeExplainer gives true Shapley values. We're not using LIME or sampling — the numbers are mathematically grounded.

8. **"Why three paths? Isn't one contestation flow enough?"** — Because real contestations aren't one thing. Sometimes the data was wrong (Path 1). Sometimes the situation has changed (Path 2). Sometimes the model shouldn't have been used at all, or the user is alleging bias (Path 3). Forcing all three into a single "re-evaluate" flow either fails Path 3 users or lies to Path 1 users. GDPR Article 22(3) and DPDP Section 11 legally require the Path 3 option — we made it first-class rather than burying it.

9. **"How do you prevent gaming — users just flipping values until approved?"** — Three mechanisms: evidence-feature binding (pay stubs can only update income, not age), anomaly checks on unrealistic deltas (>3x income jumps route to human review), and full audit trails with hashes so fraudulent approvals are prosecutable after the fact. In a real production deployment, evidence would be fetched directly from authoritative sources via Account Aggregator / DigiLocker — users never touch the artifact.

10. **"Why Ollama, not GPT-4 / Claude?"** — The LLM in Recourse has a narrow job: translate SHAP output to plain language. That doesn't need a frontier model; a local 3B parameter model handles it fine. Local-first means zero rate limits, zero network dependencies mid-demo, and zero latency tail. OpenAI is wired as a fallback. The LLM is never in the decision path — it's a translation layer at the edge.

11. **"What does your system do for models that aren't XGBoost?"** — The integration contract is four methods: `predict`, `explain`, `feature_schema`, `model_version`. Any model that honors that contract plugs in. Tree models use TreeExplainer. Linear models use coefficients directly. Black-box API-only models use KernelExplainer with sampled queries. The demo ships with XGBoost because it's fast and interpretable; the contract is framework-agnostic.

---

## 12. Things that are easy to get wrong

- **SHAP direction convention:** TreeExplainer returns contributions where positive means "pushed toward positive class." Lock down which class is "approved" at train time and be consistent in UI colouring. Nothing kills a demo faster than a green bar for something bad.
- **Recharts animation on data change:** Recharts animates on mount, not always on data change. Use `key` prop keyed on case_id + contest_round to force re-animation, or manually animate with Framer Motion's `animate` on numeric values.
- **FastAPI CORS:** Enable permissive CORS in dev (`allow_origins=["*"]`) or the frontend fetch will silently fail.
- **Model + SHAP version mismatch:** Pin versions in requirements.txt. `shap==0.44` works with `xgboost==2.0` — verify.
- **SQLite write concurrency:** Not an issue at demo scale, but use `isolation_level=None` and `PRAGMA journal_mode=WAL` if reviewers hammer it.
- **OCR timing:** Tesseract.js first load downloads 10MB of model data. Preload on app mount or the demo upload will have a 15s pause.
- **Ollama model not pulled on demo machine:** `ollama pull llama3.2:3b` takes several minutes on slow wifi. Do this the night before the demo, not during setup. If the demo laptop is different from the build laptop, export the model with `ollama save` or redo the pull in advance.
- **LLM call blocking the UI:** If the plain-language sentence awaits the LLM response before rendering the whole page, a slow Ollama startup will stutter the demo. Make the LLM call strictly async — render SHAP immediately, slot the plain-language sentence in ~500ms later with a fade-in.
- **Cache key collisions:** Cache LLM responses by a hash of the SHAP-vector (rounded to 2 decimals), not by case_id. Otherwise every new case bypasses the cache even when SHAP output is nearly identical.
- **Path 3 accidentally hitting the model:** The `/review` handler must NOT call `classifier.predict`. It only writes an audit entry and returns a queue position. This is easy to get wrong if you copy-paste from `/contest`.
- **Reason category free-text drift:** Keep `reason_category` as a hard enum on both the frontend dropdown and the backend schema. If it becomes free-text, the aggregate panel's insights become useless.

---

## 13. README content (for the repo)

Structure:
1. One-sentence pitch
2. Legal framing paragraph (CJEU, AI Act, DPDP)
3. The gap we fill (research libraries ↔ production appeals)
4. Demo GIF (record the waterfall animation)
5. Architecture diagram
6. Setup (3 commands: download data, train model, run app)
7. Attribution: DiCE, SHAP, dataset source
8. License: MIT

---

## 14. Success criteria

The build is done when:
- [ ] A denied applicant profile loads in under 2s
- [ ] Clicking Evaluate returns SHAP values and renders the waterfall in under 1s
- [ ] The PathSelector renders three clearly labeled options with reason-category dropdown
- [ ] Paths 1 and 2 trigger the animated delta that completes in ~1.5s without jank
- [ ] Path 3 writes an audit entry without calling the classifier (verified by log inspection)
- [ ] The decision chip flips colour and the confidence number tweens in sync
- [ ] Audit log shows entries with visible SHA256 hashes and the path taken
- [ ] Plain-language reasons render via Ollama with OpenAI fallback confirmed to work
- [ ] Static template fallback fires correctly when both LLM options fail (test by shutting Ollama down)
- [ ] The demo can be run end-to-end in under 90 seconds with no dev console errors

Everything beyond these ten is garnish.

---

## 15. For Claude Code specifically

- Start by scaffolding the backend. Model training script first, then API, then frontend. Don't build the UI against a stub — build it against a real running endpoint from day one.
- **Build Path 3 (`/review`) before Paths 1 and 2.** It's the simplest endpoint (write audit entry, return queue position, no classifier touched) and getting it in first means the three-path shape of the product is visible from hour one. It also forces you to get the audit log right before you're tempted to shortcut it.
- When writing the waterfall animation, build it in isolation first (Storybook-style single-component test page), get the animation clean, then integrate. Do not debug animation inside the full app flow.
- Commit after each P0 milestone. Tag a "demo-safe" commit once P0 is green so you can always revert.
- **The LLM is local-first.** Ollama runs on the demo machine, OpenAI is fallback, static templates are last resort. The only guaranteed network call is the OpenAI fallback, which should almost never fire because of the cache. The demo must be runnable with wifi off — test this explicitly at least once.
- Write the static template fallback *first*, wire the Ollama call as an enhancement on top. This way, the app works end-to-end before the LLM layer is even started, and the LLM becomes additive, not load-bearing.
- If something is taking more than 2x your estimate, cut scope. The waterfall animation is sacred; everything else can be cut.
- **Read §4a and §12 before writing any LLM code.** The scope discipline in §4a is the difference between this being a "real product" and "another GPT wrapper." The pitfalls in §12 are the actual bugs you'll hit.
- When in doubt about what to build next, reread §0 priority order. If the current task isn't on that list, you're probably scope-creeping.

---

**End of brief. Build.**
