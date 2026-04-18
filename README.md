# Recourse

A framework-agnostic portal for contesting automated decisions across five
domains. Every domain plugs in as a single adapter file and drives the UI from
the backend — no per-domain frontend code.

## Live domains

| Domain                            | Model                         | Demo reference          | DOB          |
| --------------------------------- | ----------------------------- | ----------------------- | ------------ |
| Loans / credit                    | XGBoost + SHAP (real)         | `RC-2024-A4F2-9E31`     | `12/03/1990` |
| Hiring / employment screening     | Heuristic scorer + attribution| `HR-2024-H7K2-4B19`     | `22/07/1995` |
| Creator-economy content moderation| Heuristic scorer + attribution| `CM-2024-C3M8-8F44`     | `05/11/1998` |
| University admissions / scholarship | Heuristic scorer + attribution | `UA-2024-U6A1-2D77`     | `18/02/2006` |
| Fraud detection / account freezes | Heuristic scorer + attribution| `FR-2024-F9B5-7E21`     | `30/05/1988` |

Prefix→domain: `RC`=loans, `HR`=hiring, `CM`=moderation, `UA`=admissions, `FR`=fraud.

## Running locally

### Backend (FastAPI + XGBoost + SHAP on Python 3.12)

```bash
cd backend
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python -m models.train_loans          # writes models/loans.pkl + explainer
uvicorn main:app --reload              # → http://127.0.0.1:8000
```

### Frontend (Vite + React + TS + GSAP + Zustand)

```bash
cd frontend
npm install
npm run dev                            # → http://localhost:5173
```

Append `?mock=1` to the URL to ignore the backend and run against the in-memory
mock (useful for preview without the FastAPI process).

## Demo script

1. **Login** (`RC-2024-A4F2-9E31` / `12/03/1990`). The domain selector on the
   login page lets you switch to hiring, moderation, admissions, or fraud.
2. **Step 1 — Understand.** "Why were you denied?" renders with the real SHAP
   attribution for a live XGBoost model; the other four domains render the same
   view against their heuristic scorer.
3. **Step 2 — Choose path.** Three-way fork with reason-category dropdown.
   Path 3 carries the GDPR Art 22(3) / DPDP §11 citation.
4. **Step 3 — Provide.** Humanized profile card + path-specific form. Every
   label, group, evidence option, and hint comes from the backend's
   `feature_schema`.
5. **Step 4 — Outcome.** GSAP-driven waterfall delta: bars cross the zero axis,
   decision chip flips, confidence number tweens, audit entry sealed with
   SHA-256.

A bottom-left dev bar jumps between steps and quick-logins for rehearsal.

## Architecture

```
backend/
├── adapters/
│   ├── base.py              Protocol (DomainAdapter)
│   ├── _shared.py           shared helpers + universal reason lists
│   ├── _heuristic.py        base class for rule-based adapters
│   ├── loans.py             real XGBoost + SHAP
│   ├── hiring.py            heuristic
│   ├── moderation.py        heuristic
│   ├── admissions.py        heuristic
│   ├── fraud.py             heuristic
│   └── __init__.py          REGISTRY + adapter auto-registration
├── models/
│   ├── train_loans.py       offline training + DiCE-like hint precompute
│   ├── loans.pkl            booster artifact
│   ├── loans_explainer.pkl  fitted TreeExplainer
│   └── metadata/*.json      contestability rules, hints, medians
├── routes/
│   ├── evaluate.py          /evaluate/lookup + /evaluate/domains
│   ├── contest.py           /contest (correction | new_evidence)
│   ├── review.py            /review (human path — model not re-run)
│   └── audit.py             /audit/{case_id}
├── services/
│   ├── audit_log.py         SQLite, SHA-256-chained entries
│   └── anomaly_check.py     realistic-delta bounds + demo-safe bypass
└── seed_cases.py            one demo applicant per domain

frontend/src/
├── App.tsx                  top-level stage switcher
├── store.ts                 Zustand state machine
├── components/
│   ├── LoginView.tsx        application ref + DOB login
│   ├── DomainSelector.tsx   demo picker for 5 domains
│   ├── Header.tsx           sticky brand + stepper + chip
│   ├── Stepper.tsx          4-step progress
│   ├── Step1View.tsx        "Why were you denied?"
│   ├── Step2View.tsx        path selector
│   ├── Step3View.tsx        cockpit wrapper (profile + form)
│   ├── ProfileCard.tsx      humanized profile — schema-driven
│   ├── CorrectionForm.tsx   Path 01 — schema-driven
│   ├── NewEvidenceForm.tsx  Path 02 — schema-driven
│   ├── HumanReviewForm.tsx  Path 03 — schema-driven
│   ├── Step4View.tsx        GSAP delta animation + human-review confirmation
│   ├── AuditTrail.tsx       sticky audit sidebar
│   └── DevBar.tsx           demo controls
└── lib/
    ├── api.ts               backend client + snake→camel transforms
    └── ...
```

## Adding a new domain

1. Write `backend/adapters/<name>.py` implementing the `DomainAdapter`
   protocol (either ML-backed like `LoansAdapter` or rule-based like
   `HiringAdapter` via `HeuristicAdapter`).
2. Append it to `backend/adapters/__init__.py`'s registration block.
3. Add a seed case to `backend/seed_cases.py` with a new prefix.
4. That's it — no frontend changes required. The login page's `DomainSelector`
   picks up the new domain automatically from `/evaluate/domains`.

## Legal framing

Recourse exists because automated decisions need contestation rails:

- **EU AI Act** Article 86 — right to explanation of individual decision-making.
- **CJEU *Dun & Bradstreet Austria* (Feb 2025)** — meaningful explanation of
  automated credit decisions.
- **GDPR Article 22(3)** — right to contest and obtain human intervention.
- **India DPDP Act 2023, §11** — right to a human in the loop.
- **EU DSA Article 17** — content-removal statement of reasons + appeal.
- **US FCRA §615**, **EEOC Uniform Guidelines**, **NYC Local Law 144**.

Each domain adapter surfaces its own jurisdictional hooks to the frontend.

## License

MIT.
Model Decision Contestation Interface
Automated systems deny loans, flag job applications, and moderate content - with no mechanism for users to
meaningfully contest the decision. Design a structured contestation interface that allows affected individuals to
submit counter-evidence, forces the model to re-evaluate under the new information, and produces an
explainable delta - showing exactly what changed and whether the decision flipped or held.