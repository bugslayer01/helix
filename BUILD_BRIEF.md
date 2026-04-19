# HackHelix T5 P3 — Build Brief

**Project codename:** Recourse
**Track:** T5 — Trustworthy AI & Responsible Systems
**Problem:** P3 — Model Decision Contestation Interface
**Domain scope:** Framework-agnostic; ships with two working adapters (loans — flagship, hiring — secondary) and one documented extension path (content moderation). See §2.
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

## 2. Domains — flagship, secondary, and extension

The problem statement names three domains: loans, job applications, content moderation. Building all three to demo depth is not realistic in a hackathon and produces a mediocre version of each. Instead, Recourse is architected as a **framework with pluggable domain adapters** — one config file and one model artifact per domain. Ship two working adapters and document the third as a future extension. This is a stronger pitch than pretending to do all three equally.

### Flagship: Loans / credit decisions
Deep implementation. All three contestation paths (correction, new evidence, human review) fully wired. Animated delta, full SHAP waterfall, operator panel, audit trail with hashes. This is what the judges see for 80% of the demo.

**Why loans is the flagship:**
- Public datasets exist and judges recognise them: German Credit (UCI), Give Me Some Credit (Kaggle), LendingClub.
- Features are intuitive: income, debt-to-income, employment length, credit history length. Judges don't need a legend.
- Evidence is real-world plausible: pay stubs update income, employment letters update tenure, loan payoff receipts update DTI. The submit-counter-evidence flow is legible in 30 seconds.
- Legal tailwind is sharpest here: Feb 2025 CJEU *Dun & Bradstreet Austria* ruling was literally a credit denial case.
- Stakes are legible without explanation.

### Secondary adapter: Hiring / resume screening
Lightweight implementation. Same framework, different model, different features. Used as the final 15-second "and here's the same system handling a different domain" moment in the demo. Proves the framework isn't a one-trick pony.

**Dataset:** UCI Adult (Census Income) — predicts income bracket from resume-like features (education, occupation, hours-per-week, work class). It's not literally a hiring dataset but it's the closest clean public analogue and judges have seen it.

**Scope for the hack:** Same three paths, same audit trail, same delta animation — but only one seed applicant, no operator panel, no DiCE hints. Just enough to show the adapter pattern works.

### Documented extension: Content moderation
**Do not try to build this during the hack.** Content moderation is a different architectural shape because features aren't tabular — they're text tokens or image pixels. SHAP still works (token-level attribution), but "submitting counter-evidence" means something different: providing context (account history, satire label, cultural reference) that re-runs a more expensive classifier or routes to human review.

**What ships:** A README section and a one-page architecture diagram showing how content moderation would integrate — token-level SHAP for the explanation, Path 3 (human review) as the primary contestation path since the other two don't map cleanly, a different UI variant for the evidence intake. This is the "yes we thought about it, here's how it would look" answer to the inevitable judge question, not a half-baked implementation.

### Why this scoping wins
Three adapters at equal depth = three mediocre demos. One deep + one thin + one documented = a convincing story that the framework generalizes, backed by a demo that actually works. Say this out loud in the pitch.

Do not attempt a fourth domain mid-build. Do not switch which domain is flagship mid-build.

---

## 2a. The adapter contract (Recourse Model Protocol)

Every domain is an **adapter** implementing four methods. Write a new adapter → new domain supported. No frontend changes, no API changes, no core logic changes.

```python
class DomainAdapter(Protocol):
    domain_id: str                # "loans", "hiring", "moderation"
    display_name: str             # "Loan Application", "Resume Screening"
    model_version_hash: str       # sha256 of the .pkl file

    def predict(self, features: dict) -> dict:
        """Returns {decision, confidence}"""

    def explain(self, features: dict) -> list[dict]:
        """Returns [{feature, value, contribution, contestable, evidence_types}]"""

    def feature_schema(self) -> list[dict]:
        """Returns metadata about all features — type, range, contestable, protected, evidence types"""

    def suggest_counterfactual(self, features: dict) -> list[dict]:
        """Returns DiCE-generated suggestions (optional — can return [] for simple adapters)"""
```

The frontend `PathSelector`, `CorrectionForm`, `NewEvidenceForm`, `HumanReviewForm`, and `DeltaWaterfallView` are all driven by the schema returned from `feature_schema()`. Nothing is hardcoded per domain on the UI side.

**What this means for the build:** Write the loan adapter first, get the entire flow working against it. Then write the hiring adapter as a second file. If the hiring adapter works without touching any frontend code or any core backend logic, the framework pattern is proven. If you had to modify something, the adapter contract is leaking and you need to generalize.

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
- `shap` (feature attribution at runtime)
- `dice-ml` — **used offline only, during training.** Not called at runtime. See §5 for the offline counterfactual pre-computation pattern.
- pandas, numpy
- SQLite via `sqlite3` stdlib (no ORM needed, it's a hack)
- `python-multipart` for file uploads
- `httpx` for async LLM calls
- In-memory dict for LLM response cache, pre-populated at startup. No disk cache, no extra dependency.

**LLM layer (scoped narrowly — see §4a)**
- **Primary:** Ollama running locally with `llama3.2:3b` or `qwen2.5:3b` (small, fast, reliable)
- **Fallback:** OpenAI API (gpt-4o-mini) if Ollama is unreachable or times out
- **Last resort:** Static template strings — never let the demo die because an LLM is slow

**Frontend**
- React 18 + Vite
- TypeScript (or JS if faster; consistency matters more than type safety here)
- Tailwind CSS
- **Framer Motion for all animation work, including the SHAP waterfall bars.** Do not use Recharts. The waterfall is built from pure Tailwind `div` elements with dynamic widths, colors, and positions, each wrapped in a `motion.div`. This gives frame-level control over the staggered timeline specified in §7. Recharts' internal animation engine fights multi-stage choreography and will force you into hacky re-mount workarounds — skip it.
- Zustand for state (lighter than Redux, faster to wire)

**Optional / stretch**
- Tesseract.js for OCR on uploaded pay stubs (pure frontend, no server call)

**Do not use**
- No Recharts for the waterfall — it's the wrong tool for the choreography we need
- No `dice-ml` at runtime — counterfactuals are pre-computed offline (see §5)
- No `diskcache` or other persistent cache — in-memory dict pre-populated at startup is enough
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

## 5. Data and models

Two models ship with the build — one per adapter. Both are XGBoost classifiers, trained and saved as `.pkl` artifacts. Training takes under 2 minutes per model in a notebook and is not redone at runtime.

### Loans adapter — flagship

**Dataset:** Give Me Some Credit (Kaggle) — binary classification (serious delinquency in 2 years), 150k rows, 10 features. Clean, well-known, features are legible.

Fallback: German Credit (UCI) if Kaggle download is slow — 1000 rows, 20 features, smaller but same shape.

**Features and contestability:**
- `RevolvingUtilizationOfUnsecuredLines` (DTI-adjacent, contestable)
- `age` (NOT contestable — protected attribute)
- `NumberOfTime30-59DaysPastDueNotWorse` (contestable with payment records)
- `DebtRatio` (contestable, star of the demo)
- `MonthlyIncome` (contestable, star of the demo)
- `NumberOfOpenCreditLinesAndLoans` (contestable)
- `NumberOfTimes90DaysLate` (contestable)
- `NumberRealEstateLoansOrLines` (contestable)
- `NumberOfTime60-89DaysPastDueNotWorse` (contestable)
- `NumberOfDependents` (NOT contestable — family structure)

### Hiring adapter — secondary

**Dataset:** UCI Adult (Census Income) — binary classification (income > $50k/year), 48k rows, 14 features. Public, widely used, judges recognise it.

**Features and contestability:**
- `age` (NOT contestable — protected attribute)
- `workclass` (contestable — current employment type, evidence: employment letter)
- `education` (contestable — evidence: degree certificate, transcript)
- `education_num` (contestable — derived from education)
- `marital_status` (NOT contestable — protected attribute)
- `occupation` (contestable — evidence: current job title letter)
- `relationship` (NOT contestable)
- `race` (NOT contestable — protected attribute, flagged if model uses it)
- `sex` (NOT contestable — protected attribute, flagged if model uses it)
- `capital_gain`, `capital_loss` (contestable — evidence: tax return)
- `hours_per_week` (contestable — evidence: employment letter)
- `native_country` (NOT contestable — protected attribute)

**Important:** UCI Adult contains race, sex, and native-country features that a real hiring system must never use. The adapter explicitly marks these as `protected: true` and the UI flags any non-zero SHAP contribution to them as a **bias signal** on the operator panel. This is a deliberate demo feature — it turns a problematic dataset into a teaching moment about protected attributes and surfaces the exact bias problem Recourse is designed to catch.

### Contestability metadata schema
Lives in each adapter's config file. Same shape for every adapter:

```python
CONTESTABILITY = {
  "MonthlyIncome": {
    "contestable": True,
    "protected": False,
    "evidence_types": ["pay_stub", "bank_statement"],
    "realistic_delta_multiplier": 3.0,   # flag anomaly if update exceeds 3x
    "reason": "Updatable with recent pay documentation"
  },
  "age": {
    "contestable": False,
    "protected": True,
    "evidence_types": [],
    "reason": "Protected attribute — not contestable"
  },
  # ...
}
```

### Models
- XGBoost, 100 trees, max_depth=5, for both adapters. Dump to `models/loans.pkl` and `models/hiring.pkl` with joblib.
- Accuracy target: whatever XGBoost gives out of the box. Not a Kaggle comp.
- Also save: `feature_names.json`, `shap_explainer.pkl` (pre-fit TreeExplainer) per adapter.

### SHAP integration (runtime)
Use `shap.TreeExplainer` — fast (single-digit ms for tree models), exact, no sampling. Called inline during `/evaluate` and `/contest`. This is the entire substrate of the delta visualisation.

### Counterfactual hints — offline pre-computation (NOT runtime)

DiCE generates credible case-specific hints ("changing DebtRatio to 0.28 would likely flip this") but takes 2–8 seconds per call, which will kill demo momentum. **Move DiCE entirely offline into the training script.**

During training, for each seed applicant profile:
1. Run DiCE with `method="random"` to generate 2–3 counterfactuals.
2. Serialize the results into `models/metadata/loans_hints.json` keyed by `case_id`.
3. At runtime, `/evaluate` reads the pre-computed hints from this file. Zero ML work at request time.

For any novel applicant profile not in the seed set, fall back to a simpler heuristic also computed offline:
- During training, compute the **median value of each contestable feature across all approved applicants** and store in `models/metadata/loans_medians.json`.
- At runtime, if no pre-computed DiCE hint exists for this case, serve the approved-median as the hint: "Approved applicants typically have DebtRatio below 0.31."

This hybrid keeps the pitch-level credibility of DiCE ("these hints are algorithmically derived counterfactuals") while guaranteeing sub-20ms response times for every request during the demo. The seed profiles used in the live demo always hit the pre-computed DiCE path.

**Do not call `dice_ml.Dice(...)` inside any FastAPI route.** If you see a `dice_ml` import in `backend/routes/`, that's a bug. DiCE lives in `backend/models/train_loans.py` only.

---

## 6. API contract

All endpoints return JSON. All timestamps ISO 8601. All IDs UUID v4.

### `POST /evaluate`
Initial decision.
```json
Request:
{
  "domain": "loans" | "hiring",          // selects which adapter runs
  "applicant_id": "uuid",                // optional; generated if absent
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
  "domain": "loans",
  "decision": "denied" | "approved",
  "confidence": 0.73,
  "model_version_hash": "sha256:...",     // proves which model evaluated
  "shap_values": [
    {"feature": "DebtRatio", "value": 0.42, "contribution": -0.34, "contestable": true, "protected": false},
    {"feature": "MonthlyIncome", "value": 4500, "contribution": -0.18, "contestable": true, "protected": false},
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

**Construction (important — do not use Recharts here):**
Each bar is a plain Tailwind `div` with dynamic width and background color, wrapped in a `motion.div`. Framer Motion's `animate` prop tweens `width` (as a percentage of container) and `backgroundColor` between the before-SHAP and after-SHAP states. A centered zero-axis sits in the middle of the container; positive contributions grow rightward (green), negative leftward (red). Bars that cross zero animate *through* the axis, which gives the red→green "sign flip" moment its visual punch.

```jsx
<motion.div
  className="h-6 rounded-sm"
  animate={{
    width: `${Math.abs(contribution) * scale}%`,
    backgroundColor: contribution >= 0 ? '#10b981' : '#ef4444',
    x: contribution >= 0 ? 0 : `-${Math.abs(contribution) * scale}%`,
  }}
  transition={{ duration: 1.0, ease: [0.4, 0, 0.2, 1] }}
/>
```

One row per feature, keyed by feature name so Framer Motion correctly tweens the existing elements rather than unmounting and re-mounting them.

**Other elements:**
- Above the bars: decision chip that flips color/text, synchronised with bar animation
- Above that: confidence number that tweens (e.g. 27% → 68%) via Framer Motion's `animate` on a numeric state
- Below: summary — "4 features updated, decision changed from Denied to Approved, confidence +41%"

**Animation choreography (critical — land this exactly):**
```
t=0.0s: User clicks "Re-evaluate"
t=0.1s: API response received (backend should be <200ms)
t=0.2s: Bar animation starts — each bar.motion.div begins its transition, duration 1.0s, easeInOutCubic
t=0.6s: Decision chip flip begins (Framer Motion rotateY), duration 0.4s
t=0.8s: Confidence counter starts ticking (Framer Motion animate on numeric state), duration 0.6s
t=1.4s: Everything settled, audit log entry fades in below
```
Do not let these fire simultaneously — the stagger is what makes it feel designed. Use Framer Motion's `delay` prop or `useAnimationControls` with explicit awaited `start()` calls to enforce the timeline.

### `DomainSelector` — NEW
- Top-of-page dropdown or tab: "Loan Application" / "Resume Screening"
- Switching domain reloads the applicant profile from that domain's seed data
- Purely a demo affordance so judges see the framework handling two domains
- In production this would not exist — each deployment is single-domain

### `AuditLogPanel`
- Chronological list of events for current case
- Each row: timestamp, domain, action, path taken, SHA256 hash of entry (truncated display, click to copy)
- Visible hash is worth a full point in the demo — looks like production-grade thinking

### `OperatorPanel` (stretch)
- Separate route `/operator`
- Shows aggregate across *both* adapters with domain as a filter
- "In loans, DebtRatio flipped 78% of contests → threshold recalibration candidate"
- "In hiring, 14% of SHAP contributions flagged on protected attributes (race, sex) → model audit recommended"
- The cross-domain view is part of the pitch: one pane of glass for every automated decision system in the company

---

## 8. The demo money shot — full script

105-second demo sequence. Rehearse this exact flow.

1. **(0:00–0:12)** Pitch opener. "The problem statement names three domains — loans, hiring, content moderation. Rather than build three mediocre demos, we built a framework with two working domain adapters and one documented extension path. In February 2025, the EU Court of Justice ruled that companies must provide meaningful explanations of automated decisions. India's DPDP Act Section 11 guarantees the right to human intervention. No production system does this today. We built it — once, portable across every automated decision system a company runs."

2. **(0:12–0:22)** Show loan applicant profile. Click Evaluate. Red "Denied" chip appears. SHAP waterfall renders — DebtRatio at -0.34 is the screaming red bar at the top. Plain-language reason appears below (from local Ollama): "Your debt-to-income ratio was the primary factor..."

3. **(0:22–0:32)** Click Contest. **Path selector appears with three options.** Narrate: "The user chooses the shape of their contest — correct wrong data, add new evidence, or escalate to a human. Each path triggers a different pipeline." Select "Correct existing information."

4. **(0:32–0:48)** Correction form. Flag DebtRatio as incorrect — "the existing loan was actually paid off but the credit bureau hadn't updated." Enter 0.28. Select evidence type: "loan payoff receipt." Call out the locked age and dependents fields — "protected attributes, system-enforced not contestable."

5. **(0:48–1:05)** Click Re-evaluate. **The money shot.** Bars animate — DebtRatio's red bar shrinks, crosses zero, becomes a green bar at +0.12. Decision chip flips red→green. Confidence number tweens 27% → 68%. Audit log entry fades in with SHA256 hash. Reason category ("stale_data") is visible in the audit row.

6. **(1:05–1:18)** Show Path 3 quickly. Reset to the original denial. Click "Request human review" this time. Select reason: "protected_attribute_bias." Show that *no model re-run happens* — submission goes to a queue with a timestamp and hash. Narrate: "This is the GDPR Article 22(3) path. Sometimes the user's complaint isn't about inputs — it's about the model itself being the wrong tool. We route those to humans, not back into the same black box."

7. **(1:18–1:33)** **Domain switch moment.** Click the DomainSelector, switch to "Resume Screening." A different applicant profile loads — UCI Adult features. Click Evaluate. Denied again, but this time the waterfall shows a small negative SHAP contribution on *sex* — which the operator panel at the bottom flags in red. Narrate: "Same framework, different model, different domain. And look what it caught — the underlying hiring model has a non-zero attribution to a protected attribute. Recourse surfaces bias no one-off audit would find. Same three paths, same audit trail, same animated delta. One adapter per domain."

8. **(1:33–1:45)** Operator view. "Across both domains: loans show 62% of contests are corrections — data pipeline freshness issue. Hiring shows protected-attribute leakage in the base model. Content moderation is documented as a future extension — different feature shape, same framework pattern. This is the accountability layer that turns individual recourse into institutional feedback. Thank you."

---

## 9. File structure

```
recourse/
├── backend/
│   ├── main.py                  # FastAPI app + route registration + adapter registry
│   ├── adapters/                # One file per domain adapter
│   │   ├── base.py              # DomainAdapter Protocol (the contract)
│   │   ├── loans.py             # Flagship adapter
│   │   ├── hiring.py            # Secondary adapter
│   │   └── __init__.py          # Registers all adapters at startup
│   ├── models/
│   │   ├── train_loans.py       # Training + offline DiCE pre-compute + medians
│   │   ├── train_hiring.py      # Same pattern for hiring
│   │   ├── loans.pkl            # Committed artifact
│   │   ├── loans_explainer.pkl
│   │   ├── hiring.pkl
│   │   ├── hiring_explainer.pkl
│   │   └── metadata/
│   │       ├── loans.json            # Contestability map per domain
│   │       ├── loans_hints.json      # Pre-computed DiCE counterfactuals per seed case_id
│   │       ├── loans_medians.json    # Approved-median fallback per feature
│   │       ├── hiring.json
│   │       ├── hiring_hints.json
│   │       └── hiring_medians.json
│   ├── routes/
│   │   ├── evaluate.py          # Accepts domain parameter, dispatches to adapter
│   │   ├── contest.py           # Handles contest_path: correction | new_evidence
│   │   ├── review.py            # Path 3 — human review queue
│   │   ├── audit.py
│   │   └── aggregate.py         # Cross-domain aggregation
│   ├── services/
│   │   ├── audit_log.py         # SQLite writer + hasher
│   │   ├── anomaly_check.py     # Realistic-delta bounds + DEMO_SAFE_CASE_IDS bypass
│   │   ├── llm_helper.py        # Ollama primary → OpenAI fallback → template
│   │   └── llm_cache.py         # In-memory dict, pre-populated at startup
│   ├── db/
│   │   └── audit.db             # SQLite — gitignored
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── DomainSelector.tsx              # NEW — switch loans / hiring
│   │   │   ├── ApplicantProfileView.tsx
│   │   │   ├── PathSelector.tsx                # three-path fork
│   │   │   ├── CorrectionForm.tsx              # Path 1
│   │   │   ├── NewEvidenceForm.tsx             # Path 2
│   │   │   ├── HumanReviewForm.tsx             # Path 3
│   │   │   ├── HumanReviewConfirmation.tsx     # Path 3 success screen
│   │   │   ├── DeltaWaterfallView.tsx
│   │   │   ├── AuditLogPanel.tsx
│   │   │   └── OperatorPanel.tsx
│   │   ├── lib/
│   │   │   ├── api.ts           # Fetch wrappers
│   │   │   └── store.ts         # Zustand state (includes current domain)
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
- `DomainAdapter` Protocol defined in `adapters/base.py`
- **Loan adapter** fully implemented — model trained, artifacts saved, `predict` / `explain` / `feature_schema` all wired
- **Offline counterfactual pre-compute** — `train_loans.py` runs DiCE for each seed case and writes `loans_hints.json`; also writes `loans_medians.json` from approved-applicant medians as the novel-input fallback
- `/evaluate` endpoint accepting `domain` parameter, dispatching to registered adapter, reading pre-computed hints from metadata
- `/contest` endpoint accepting `contest_path` (correction or new_evidence), returning delta
- `/review` endpoint for Path 3 — writes audit entry, does NOT call any adapter
- **`PathSelector` component** rendering the three-path fork
- `ApplicantProfileView`, `CorrectionForm`, `NewEvidenceForm`, `HumanReviewForm`, `DeltaWaterfallView`
- **Waterfall built from Tailwind divs + Framer Motion** (no Recharts) with the §7 choreography landing cleanly — non-negotiable
- Basic audit log (write to SQLite with domain tag, show in UI, distinguishes path taken)
- Static-template LLM fallback (no live LLM needed for P0 — ship the templates first)
- Seed data: 3 pre-loaded loan applicant profiles for demo

### P1 — should ship (aim: next 25%)
- **Hiring adapter** — `hiring.py` implementing the same protocol, UCI Adult model trained and saved, `hiring_hints.json` and `hiring_medians.json` generated offline
- `DomainSelector` frontend component — switch between loans and hiring
- 1 seed applicant profile for hiring (one is enough for the demo moment)
- SHA256 hashing of audit entries, visible in UI
- Pre-computed DiCE hints rendering in correction and new-evidence forms (both domains)
- Ollama integration with async non-blocking calls for plain-language reasons
- **In-memory dict cache** for LLM responses, pre-populated at FastAPI startup for all seed cases (keyed by `(domain, normalized_shap_hash)` — see §12 for the normalization recipe)
- OpenAI fallback wired in with 2s timeout on Ollama
- Locked feature indicators in UI (age, dependents on loans; race, sex, native-country on hiring)
- Protected-attribute bias flag on OperatorPanel when SHAP contribution on protected features exceeds 0.05
- Polished styling (Tailwind, dark mode looks good in demo)

### P2 — stretch (remaining 15%)
- OCR-based evidence upload (Tesseract.js)
- Anomaly-check circuit breaker (realistic-delta bounds) that routes outliers to human review — **with a `DEMO_SAFE_CASE_IDS` allowlist that bypasses the check for the live demo profiles**, so the main flow never aborts unexpectedly
- `OperatorPanel` with cross-domain aggregate view segmented by contest path
- Multiple contestation rounds on same case
- Export audit trail as PDF
- Content moderation adapter as a README architecture diagram only — do NOT try to implement this

**Cut ruthlessly if time compresses.** P0 (loan adapter + three-path flow + div-based animated delta + audit log) is the minimum viable demo. If the hiring adapter isn't ready at T-6hrs, cut it and lean harder on the "documented extension path" narrative for both hiring and moderation. Do not ship a half-working hiring adapter.

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

10. **"Why Ollama, not a hosted frontier LLM?"** — The LLM in Recourse has a narrow job: translate SHAP output to plain language. That doesn't need a frontier model; a local 3B parameter model handles it fine. Local-first means zero rate limits, zero network dependencies mid-demo, and zero latency tail. OpenAI is wired as a fallback. The LLM is never in the decision path — it's a translation layer at the edge.

11. **"What does your system do for models that aren't XGBoost?"** — The integration contract is four methods: `predict`, `explain`, `feature_schema`, `model_version`. Any model that honors that contract plugs in. Tree models use TreeExplainer. Linear models use coefficients directly. Black-box API-only models use KernelExplainer with sampled queries. The demo ships with XGBoost because it's fast and interpretable; the contract is framework-agnostic.

---

## 12. Things that are easy to get wrong

- **SHAP direction convention:** TreeExplainer returns contributions where positive means "pushed toward positive class." Lock down which class is "approved" at train time and be consistent in UI colouring. Nothing kills a demo faster than a green bar for something bad.
- **Framer Motion with mapped keys:** When rendering the waterfall bars from an array of features, Framer Motion needs each `motion.div` to have a stable `key` prop matching the feature name — not the array index. Otherwise, when the after-state reorders features by magnitude, Framer Motion will tween between the wrong pairs of bars and you'll get a chaotic-looking animation. Sort features by stable criteria (e.g., feature name) and let CSS ordering handle visual sort if needed.
- **FastAPI CORS:** Enable permissive CORS in dev (`allow_origins=["*"]`) or the frontend fetch will silently fail.
- **Model + SHAP version mismatch:** Pin versions in requirements.txt. `shap==0.44` works with `xgboost==2.0` — verify.
- **SQLite write concurrency:** Not an issue at demo scale, but use `isolation_level=None` and `PRAGMA journal_mode=WAL` if reviewers hammer it.
- **OCR timing:** Tesseract.js first load downloads 10MB of model data. Preload on app mount or the demo upload will have a 15s pause.
- **Ollama model not pulled on demo machine:** `ollama pull llama3.2:3b` takes several minutes on slow wifi. Do this the night before the demo, not during setup. If the demo laptop is different from the build laptop, redo the pull in advance.
- **LLM call blocking the UI:** If the plain-language sentence awaits the LLM response before rendering the whole page, a slow Ollama startup will stutter the demo. Make the LLM call strictly async — render SHAP immediately, slot the plain-language sentence in ~500ms later with a fade-in.
- **Cache key collisions from float precision:** SHAP values are floats; `0.34000001` and `0.34000000` hash differently and will cause every "identical" input to miss the cache. Normalize before hashing with this exact recipe:
  ```python
  def cache_key(domain: str, shap_values: list[dict]) -> str:
      normalized = [
          (v["feature"], round(v["contribution"], 1), round(v["value"], 1))
          for v in shap_values
      ]
      normalized.sort(key=lambda t: t[0])  # sort alphabetically by feature name
      return f"{domain}:{hashlib.sha256(repr(normalized).encode()).hexdigest()}"
  ```
  Round to 1 decimal (0.1 granularity is sufficient for "same case"), sort before hashing, include domain as a key prefix. Test with two slightly different float inputs before trusting it.
- **Path 3 accidentally hitting the model:** The `/review` handler must NOT call `classifier.predict`. It only writes an audit entry and returns a queue position. Easy to get wrong if you copy-paste from `/contest`.
- **Reason category free-text drift:** Keep `reason_category` as a hard enum on both the frontend dropdown and the backend schema. If it becomes free-text, the aggregate panel's insights become useless.
- **Anomaly check firing during the live demo:** The realistic-delta check is a production feature, not a demo feature. If you type a value that crosses the threshold during your pitch, Path 1 will abort and dump into Path 3, destroying the money shot. Implement a `DEMO_SAFE_CASE_IDS: set[str]` allowlist in `anomaly_check.py` — if the incoming `case_id` is in the set, skip the check entirely. Populate this set with the 3 seed case IDs. The anomaly logic still exists for judge Q&A about fraud prevention; the demo just never triggers it.
- **Pre-computed hints missing for a case:** `/evaluate` must gracefully fall back to the approved-median heuristic when `loans_hints.json` has no entry for the `case_id`. Do not 500 on a missing hint — the hint is a UX enhancement, not a core requirement.

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
- [ ] Clicking Evaluate returns SHAP values and renders the waterfall in under 1s (backend response under 200ms — no live DiCE calls)
- [ ] The PathSelector renders three clearly labeled options with reason-category dropdown
- [ ] Paths 1 and 2 trigger the div-based animated delta that completes in ~1.5s without jank
- [ ] Path 3 writes an audit entry without calling the classifier (verified by log inspection)
- [ ] The decision chip flips colour and the confidence number tweens in sync
- [ ] Audit log shows entries with visible SHA256 hashes and the path taken
- [ ] Plain-language reasons render via Ollama with OpenAI fallback confirmed to work
- [ ] Static template fallback fires correctly when both LLM options fail (test by shutting Ollama down)
- [ ] LLM cache hits for the 3 seed cases on repeated requests (test by restarting the server and immediately hitting evaluate twice)
- [ ] Pre-computed DiCE hints are loaded at startup and served from `loans_hints.json` (no live `dice_ml.Dice(...)` call appears in the `/evaluate` code path)
- [ ] Anomaly check is present in the codebase but bypassed for the `DEMO_SAFE_CASE_IDS` allowlist (verified by attempting a large update on a demo case and seeing it proceed normally)
- [ ] The demo can be run end-to-end in under 105 seconds with no dev console errors

Everything beyond these thirteen is garnish.

---

## 15. For the builder specifically

- Start by scaffolding the backend. Model training script first, then API, then frontend. Don't build the UI against a stub — build it against a real running endpoint from day one.
- **Build the `DomainAdapter` Protocol in `adapters/base.py` before anything else.** The entire backend then reads that contract. If you skip this step and hardcode "loans" everywhere, retrofitting the hiring adapter later will be painful.
- **Build the loan adapter end-to-end first — through to a working animated delta — before you even start the hiring adapter.** Do not build both in parallel. The loan flow is the demo's center of gravity; the hiring adapter is only meaningful *after* the loan one works, because its value is proving that the framework generalizes.
- **Build Path 3 (`/review`) before Paths 1 and 2.** It's the simplest endpoint (write audit entry, return queue position, no classifier touched) and getting it in first means the three-path shape of the product is visible from hour one. It also forces you to get the audit log right before you're tempted to shortcut it.
- **Run DiCE only inside `train_loans.py` / `train_hiring.py`.** At runtime, load pre-computed hints from JSON. If `import dice_ml` appears anywhere under `backend/routes/`, that's a bug — fix it before moving on. The only reason the runtime is fast enough for a live demo is because ML work is entirely offline.
- **Build the waterfall from Tailwind `div`s wrapped in `motion.div`.** Do not import Recharts for this component. Frame-level control over the §7 choreography requires direct access to each bar's animation state. Build it in isolation first (single-component test page), get the animation clean, then integrate. Do not debug animation inside the full app flow.
- **When you add the hiring adapter, only touch `backend/adapters/hiring.py`, `backend/models/train_hiring.py`, `backend/models/metadata/hiring*.json`, and the adapter registry.** If you find yourself editing any frontend component, any route file, or any service file to make hiring work — stop and generalize first. That's the contract leaking.
- Commit after each P0 milestone. Tag a "demo-safe" commit once P0 is green so you can always revert.
- **The LLM is local-first.** Ollama runs on the demo machine, OpenAI is fallback, static templates are last resort. The only guaranteed network call is the OpenAI fallback, which should almost never fire because of the in-memory cache. The demo must be runnable with wifi off — test this explicitly at least once.
- Write the static template fallback *first*, wire the Ollama call as an enhancement on top. This way, the app works end-to-end before the LLM layer is even started, and the LLM becomes additive, not load-bearing.
- **The LLM cache is a plain Python dict pre-populated at FastAPI startup** for the 3 seed case SHAP fingerprints. No `diskcache`, no `lru_cache`, no persistence. Server restarts wipe it, which is what you want during iteration.
- **Populate `DEMO_SAFE_CASE_IDS` with the seed case UUIDs before the live demo.** The anomaly check must skip these cases. If you forget this step and type an unrealistic update during the pitch, the demo will abort into Path 3 and you'll lose the audience. This is the single highest-leverage safety check in the whole brief.
- If something is taking more than 2x your estimate, cut scope. The waterfall animation is sacred; everything else can be cut — **including the hiring adapter.** Loans alone with three paths and a clean demo beats two half-working adapters.
- **Read §4a and §12 before writing any LLM code.** The scope discipline in §4a is the difference between this being a "real product" and "another GPT wrapper." The pitfalls in §12 are the actual bugs you'll hit.
- When in doubt about what to build next, reread §0 priority order. If the current task isn't on that list, you're probably scope-creeping.
- **Read §4a and §12 before writing any LLM code.** The scope discipline in §4a is the difference between this being a "real product" and "another GPT wrapper." The pitfalls in §12 are the actual bugs you'll hit.
- When in doubt about what to build next, reread §0 priority order. If the current task isn't on that list, you're probably scope-creeping.

---

**End of brief. Build.**
