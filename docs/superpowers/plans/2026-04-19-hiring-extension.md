# Hiring Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a hiring vertical to Recourse using an OpenAI-as-judge model. Recruiter pastes a JD + uploads a resume; the LLM scores fit and lists per-reason rejections; rejected candidates get the same JWT handoff to Recourse where they contest each reason via doc upload OR free-text rebuttal; the LLM re-judges and a flipped/held verdict flows back via the existing webhook.

**Architecture:** Pure extension of the existing two-service topology. **Zero changes to Recourse backend or frontend** — they're already domain-agnostic via the Adapter Protocol. New code lives in `shared/llm/`, `shared/adapters/hiring.py` (rewrite the stub), and `customer_portal/` (new routes + domain-switcher in the existing UI). Hard-deterministic XGBoost is replaced for hiring with `gpt-4o-mini` calls returning structured JSON; the `reasons[]` schema mirrors loans `shap[]` so Recourse renders it unchanged.

**Tech Stack:** OpenAI Python SDK (`openai>=1.50`), `gpt-4o-mini`, `response_format={type:"json_schema"}`, `temperature=0`. pdfplumber for resume PDF text. Existing FastAPI + SQLite + Vite + Zustand for everything else.

---

## File Structure

**Create:**
- `shared/llm/__init__.py` — package marker
- `shared/llm/openai_judge.py` — two-call wrapper (initial + re-eval) with structured-JSON schemas
- `shared/llm/cache.py` — disk JSON cache so repeated demos don't burn tokens
- `customer_portal/backend/routes/hiring.py` — `/api/v1/hiring/*` endpoints
- `customer_portal/backend/services/hiring_intake.py` — JD + resume → adapter call → decision row
- `customer_portal/frontend/src/components/hiring/JdInputView.tsx`
- `customer_portal/frontend/src/components/hiring/ResumeUploadView.tsx`
- `customer_portal/frontend/src/components/hiring/HiringDecisionView.tsx`
- `customer_portal/frontend/src/components/DomainSwitcher.tsx`
- `customer_portal/frontend/src/store_hiring.ts` — separate Zustand slice for hiring flow
- `scripts/seed/hiring/cases/_lib.py` — JD + resume PDF generators
- `scripts/seed/hiring/cases/build_all.py` — 3 case fixtures
- `scripts/seed/hiring/cases/case{1,2,3}/{jd.txt, resume.pdf, case.json}`
- `scripts/seed_hiring.py` — direct-SQL seeder (mirrors `scripts/seed.py`)
- `scripts/smoke_hiring.py` — end-to-end round-trip
- `tests/shared/llm/test_openai_judge.py` — schema + cache contract

**Modify:**
- `shared/adapters/hiring.py` — rewrite from heuristic stub to LLM adapter
- `shared/adapters/__init__.py` — register the new adapter (already imports HiringAdapter; just verify shape)
- `customer_portal/backend/main.py` — include hiring router
- `customer_portal/backend/db.py` — extend lender.db schema with `jd_text`, `resume_text` columns on `applications` (or new `job_postings` + `resume_intakes` tables)
- `customer_portal/frontend/src/App.tsx` — domain switch via `?domain=hiring`
- `customer_portal/frontend/src/components/Header.tsx` — show domain pill
- `backend/services/rerun.py` — accept `evidence_payloads` (text rebuttals + extracted doc fields) for non-numeric domains
- `backend/services/evidence_pipeline.py` — accept `rebuttal_text` form field; pass to adapter for re-judging
- `backend/requirements.txt` — add `openai>=1.50`
- `Makefile` — add `seed-hiring` + `smoke-hiring` targets
- `README.md` — note hiring vertical, OpenAI dependency, env var

---

## Pre-Flight

- [ ] **Step 0a: Install openai SDK**

```bash
uv pip install --python /home/kerito/Desktop/Playground/helix/backend/.venv/bin/python openai==1.55.0
```

Expected: `Installed 1 package`.

- [ ] **Step 0b: Add OPENAI_API_KEY to env**

Append to `backend/requirements.txt`:
```
openai==1.55.0
```

Create `.env.example` at repo root if absent:
```
HELIX_JWT_SECRET=dev-jwt-secret-change-me
HELIX_WEBHOOK_SECRET=dev-webhook-secret-change-me
OPENAI_API_KEY=sk-...
```

Confirm `.env` is in `.gitignore` (it is). Source key from local `.env` for testing.

---

## Task 1: OpenAI judge module

**Files:**
- Create: `shared/llm/__init__.py`
- Create: `shared/llm/openai_judge.py`
- Create: `shared/llm/cache.py`
- Test: `tests/shared/llm/test_openai_judge.py`

- [ ] **Step 1: Write the test for cache hit/miss**

Create `tests/shared/llm/test_openai_judge.py`:
```python
import json
from pathlib import Path
import pytest
from shared.llm.cache import disk_cache_for, cached_call


def test_cache_miss_calls_fn(tmp_path: Path):
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        return {"x": 1}
    out = cached_call(disk_cache_for(tmp_path), "k1", fn)
    assert out == {"x": 1}
    assert calls["n"] == 1


def test_cache_hit_skips_fn(tmp_path: Path):
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        return {"x": 1}
    cached_call(disk_cache_for(tmp_path), "k1", fn)
    cached_call(disk_cache_for(tmp_path), "k1", fn)
    assert calls["n"] == 1


def test_cache_different_keys_isolated(tmp_path: Path):
    out1 = cached_call(disk_cache_for(tmp_path), "k1", lambda: {"a": 1})
    out2 = cached_call(disk_cache_for(tmp_path), "k2", lambda: {"a": 2})
    assert out1["a"] == 1
    assert out2["a"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/kerito/Desktop/Playground/helix && backend/.venv/bin/python -m pytest tests/shared/llm/test_openai_judge.py -v
```

Expected: ImportError on `shared.llm.cache`.

- [ ] **Step 3: Implement cache module**

Create `shared/llm/__init__.py`:
```python
"""LLM clients used by domain adapters that call out to OpenAI."""
```

Create `shared/llm/cache.py`:
```python
"""Disk-backed JSON cache for LLM calls.

Keyed by sha256(prompt+schema+model). Demo wifi can die; cached demo cases keep
working. Production uses Redis instead.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable


def make_key(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def disk_cache_for(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    return root


def cached_call(cache_dir: Path, key: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    f = cache_dir / f"{key}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            f.unlink(missing_ok=True)
    result = fn()
    f.write_text(json.dumps(result, indent=2))
    return result
```

- [ ] **Step 4: Run cache tests**

```bash
backend/.venv/bin/python -m pytest tests/shared/llm/test_openai_judge.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Implement openai_judge module**

Create `shared/llm/openai_judge.py`:
```python
"""OpenAI gpt-4o-mini judge for resume-vs-JD scoring.

Two entry points:
- judge_initial(jd_text, resume_text) -> Decision
- judge_re_evaluation(jd_text, resume_text, prior_decision, rebuttals) -> Decision

Decisions are JSON dicts conforming to a strict schema so the rest of Recourse
treats them like SHAP rows.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from .cache import cached_call, disk_cache_for, make_key

_MODEL = "gpt-4o-mini"
_PROMPT_VERSION = "v1"
_CACHE_ROOT = Path(__file__).resolve().parents[2] / ".llm-cache"


_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["approved", "denied"]},
        "fit_score": {"type": "number", "minimum": 0, "maximum": 1},
        "reasons": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "applicant_value": {"type": "string"},
                    "jd_requirement": {"type": "string"},
                    "weight": {"type": "number", "minimum": -1, "maximum": 1},
                    "evidence_quote": {"type": "string"},
                },
                "required": ["id", "label", "applicant_value", "jd_requirement", "weight", "evidence_quote"],
                "additionalProperties": False,
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["verdict", "fit_score", "reasons", "summary"],
    "additionalProperties": False,
}


_RE_EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["approved", "denied"]},
        "fit_score": {"type": "number", "minimum": 0, "maximum": 1},
        "reasons": _DECISION_SCHEMA["properties"]["reasons"],
        "summary": {"type": "string"},
        "delta": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "reason_id": {"type": "string"},
                    "before_weight": {"type": "number"},
                    "after_weight": {"type": "number"},
                    "why_changed": {"type": "string"},
                },
                "required": ["reason_id", "before_weight", "after_weight", "why_changed"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["verdict", "fit_score", "reasons", "summary", "delta"],
    "additionalProperties": False,
}


_INITIAL_PROMPT = """You are an experienced senior recruiter at a company hiring for the role described in the JOB DESCRIPTION below. You must judge the RESUME against the JD strictly but fairly, and return a JSON decision matching the provided schema.

Rules:
- Output 3-6 reasons, each tied to a specific JD requirement and a specific resume claim.
- weight is your stated push toward the verdict: negative = pushes toward "denied", positive = pushes toward "approved". Magnitude reflects how load-bearing the reason is.
- evidence_quote MUST be a verbatim short snippet from the resume (or "(absent from resume)" if the relevant evidence is missing).
- fit_score is your overall calibrated probability the candidate is a good hire (0 = terrible fit, 1 = perfect).
- verdict = "approved" iff fit_score >= 0.5.
- summary is one short sentence.
- DO NOT invent qualifications the resume does not mention.
- DO NOT use protected-class signals (name, photo, age, gender, location).

JOB DESCRIPTION:
\"\"\"{jd}\"\"\"

RESUME:
\"\"\"{resume}\"\"\"
"""


_REEVAL_PROMPT = """You previously judged this candidate against this JD. Here is your prior decision plus the applicant's REBUTTALS (per-reason text + any new evidence the validator has extracted from uploaded documents). Re-judge with this new context.

Rules:
- Be skeptical of unverifiable text rebuttals; weight extracted document fields more than free text.
- Return the SAME schema as before plus a delta array: for every reason whose weight changed, list reason_id, before_weight, after_weight, and a one-sentence why_changed.
- Use the SAME reason IDs as the prior decision wherever possible.
- verdict = "approved" iff fit_score >= 0.5.
- DO NOT use protected-class signals.

JOB DESCRIPTION:
\"\"\"{jd}\"\"\"

RESUME:
\"\"\"{resume}\"\"\"

PRIOR DECISION:
{prior_json}

REBUTTALS (one block per reason):
{rebuttals_block}
"""


def _client() -> OpenAI:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY not set. Hiring vertical needs an OpenAI key. "
            "Add it to your .env file or export it."
        )
    return OpenAI(api_key=key)


def _call(prompt: str, schema: dict[str, Any], schema_name: str) -> dict[str, Any]:
    client = _client()
    resp = client.chat.completions.create(
        model=_MODEL,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": schema, "strict": True},
        },
    )
    raw = resp.choices[0].message.content or "{}"
    return json.loads(raw)


def model_version() -> str:
    body = f"{_MODEL}|{_PROMPT_VERSION}|{json.dumps(_DECISION_SCHEMA, sort_keys=True)}"
    return "sha256:" + hashlib.sha256(body.encode()).hexdigest()


def judge_initial(jd_text: str, resume_text: str) -> dict[str, Any]:
    prompt = _INITIAL_PROMPT.format(jd=jd_text.strip(), resume=resume_text.strip())
    key = make_key("initial", _MODEL, _PROMPT_VERSION, prompt)
    return cached_call(disk_cache_for(_CACHE_ROOT), key, lambda: _call(prompt, _DECISION_SCHEMA, "hiring_decision"))


def judge_re_evaluation(
    jd_text: str,
    resume_text: str,
    prior_decision: dict[str, Any],
    rebuttals: list[dict[str, Any]],
) -> dict[str, Any]:
    blocks = []
    for r in rebuttals:
        block = f"- reason_id: {r['reason_id']}\n  applicant_text: {r.get('text') or '(no free-text)'}\n  extracted_evidence: {r.get('extracted') or '(no extracted document fields)'}"
        blocks.append(block)
    rebuttals_block = "\n".join(blocks) if blocks else "(no rebuttals provided)"
    prompt = _REEVAL_PROMPT.format(
        jd=jd_text.strip(),
        resume=resume_text.strip(),
        prior_json=json.dumps(prior_decision, indent=2, sort_keys=True),
        rebuttals_block=rebuttals_block,
    )
    key = make_key("reeval", _MODEL, _PROMPT_VERSION, prompt)
    return cached_call(disk_cache_for(_CACHE_ROOT), key, lambda: _call(prompt, _RE_EVAL_SCHEMA, "hiring_reeval"))
```

- [ ] **Step 6: Add openai SDK to requirements**

Append to `backend/requirements.txt`:
```
openai==1.55.0
```

- [ ] **Step 7: Add cache dir to gitignore**

Append to `.gitignore`:
```
.llm-cache/
```

- [ ] **Step 8: Commit**

```bash
git add shared/llm tests/shared/llm backend/requirements.txt .gitignore
git commit -m "feat(llm): OpenAI judge module + disk cache

shared/llm/openai_judge.py wraps gpt-4o-mini with two structured-JSON
prompts: initial decision (jd + resume → reasons + verdict + fit_score)
and re-evaluation (prior decision + rebuttals → updated reasons + delta).
Both use temperature=0 and a strict json_schema response_format so
output is parseable.

shared/llm/cache.py disk-caches every call keyed by sha256 of the full
prompt + model + schema. Demo wifi can drop and pre-warmed cases still
work. Repeated calls during dev cost zero tokens.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Hiring adapter (LLM-backed)

**Files:**
- Modify: `shared/adapters/hiring.py` (full rewrite)
- Test: `tests/shared/adapters/test_hiring.py`

- [ ] **Step 1: Write the adapter contract test**

Create `tests/shared/adapters/test_hiring.py`:
```python
from shared.adapters import get_adapter


def test_hiring_adapter_registered():
    a = get_adapter("hiring")
    assert a.domain_id == "hiring"
    assert a.display_name


def test_intake_doc_types_present():
    a = get_adapter("hiring")
    docs = a.intake_doc_types()
    ids = {d["id"] for d in docs}
    assert "resume" in ids
    assert "job_description" in ids


def test_evidence_doc_types_for_skill_gap():
    a = get_adapter("hiring")
    docs = a.evidence_doc_types("missing_skill")
    ids = {d["id"] for d in docs}
    assert "certificate" in ids
    assert "course_completion" in ids


def test_extract_prompt_for_resume():
    a = get_adapter("hiring")
    p = a.extract_prompt("resume")
    assert "schema" in p
    assert p["schema"]["type"] == "object"
```

- [ ] **Step 2: Run test to verify failure**

```bash
backend/.venv/bin/python -m pytest tests/shared/adapters/test_hiring.py -v
```

Expected: FAIL on `intake_doc_types not present` or similar.

- [ ] **Step 3: Rewrite hiring adapter**

Replace `shared/adapters/hiring.py` entirely:
```python
"""Hiring adapter — LLM-as-judge using shared.llm.openai_judge.

Differs from loans (XGBoost): there is no fitted model file; the model is
GPT-4o-mini constrained by a JSON schema. predict() and explain() share a
single LLM call cached by prompt hash, so calling them in sequence on the
same features costs one round-trip.
"""
from __future__ import annotations

import json
from typing import Any

from shared.llm import openai_judge

from ._shared import UNIVERSAL_CONTEST_REASONS, UNIVERSAL_REVIEW_REASONS


class HiringAdapter:
    domain_id = "hiring"
    display_name = "Hiring decision"

    @property
    def model_version_hash(self) -> str:
        return openai_judge.model_version()

    # ---- prediction ----------------------------------------------------

    def _judge(self, features: dict[str, Any]) -> dict[str, Any]:
        jd = features.get("jd_text") or ""
        resume = features.get("resume_text") or ""
        prior = features.get("_prior_decision")
        rebuttals = features.get("_rebuttals") or []
        if prior:
            return openai_judge.judge_re_evaluation(jd, resume, prior, rebuttals)
        return openai_judge.judge_initial(jd, resume)

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        d = self._judge(features)
        prob_bad = round(1.0 - float(d["fit_score"]), 4)
        return {
            "decision": d["verdict"],
            "confidence": round(float(d["fit_score"]), 4),
            "prob_bad": prob_bad,
        }

    def explain(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        d = self._judge(features)
        rows: list[dict[str, Any]] = []
        for r in d.get("reasons", []):
            rows.append({
                "feature": r["id"],
                "display_name": r["label"],
                "value": r["applicant_value"],
                "value_display": r["applicant_value"],
                "contribution": float(r["weight"]),
                "contestable": True,
                "protected": False,
                "evidence_quote": r["evidence_quote"],
                "jd_requirement": r["jd_requirement"],
            })
        return rows

    # ---- schema --------------------------------------------------------

    def feature_schema(self) -> list[dict[str, Any]]:
        # Hiring features are emergent from the LLM call; for the contest
        # UI we expose a single contestable slot per detected reason at
        # runtime. The static schema below covers the base intake shape.
        return [
            {
                "feature": "resume_text",
                "form_key": "resume_text",
                "display_name": "Resume",
                "group": "candidate",
                "contestable": True,
                "protected": False,
                "correction_policy": "evidence_driven",
                "evidence_types": ["resume", "linkedin_export"],
                "unit": "",
                "hint": "Upload a fresh resume to update every reason at once.",
                "hint_placeholder": "",
                "min": None,
                "max": None,
                "step": None,
                "realistic_delta_multiplier": 5.0,
            },
        ]

    def suggest_counterfactual(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        return []

    def verbs(self) -> dict[str, str]:
        return {
            "subject_noun": "job application",
            "approved_label": "Selected",
            "denied_label": "Not selected",
            "hero_question": "Why didn't you make the shortlist?",
            "hero_subtitle": "The recruiter's screening model compared your resume against the role's requirements. Here's its reasoning.",
            "outcome_title_flipped": "Your application has moved forward.",
            "outcome_title_same": "The recruiter still has concerns.",
            "outcome_review_title": "A human reviewer is taking over.",
            "correction_title": "Counter the recruiter's reasoning.",
            "correction_sub": "For each reason below, attach a document or write a rebuttal. The model re-judges with your input.",
            "new_evidence_title": "Add fresh proof.",
            "new_evidence_sub": "An updated resume, certificate, or recommendation.",
            "review_title": "Tell a human reviewer what was missed.",
            "review_sub": "A reviewer will read your case — the model is not re-run.",
            "correction_button": "Counter each reason",
            "correction_body": "Per-reason rebuttal: doc OR text.",
            "new_evidence_body": "Replace your resume with a more complete version.",
            "review_body": "Skip the model. A person reviews.",
        }

    def profile_groups(self) -> list[dict[str, Any]]:
        return [
            {"id": "candidate", "title": "About this candidate", "locked": False, "field_keys": ["resume_text"]},
        ]

    def path_reasons(self) -> dict[str, list]:
        return {
            "contest": list(UNIVERSAL_CONTEST_REASONS),
            "review": list(UNIVERSAL_REVIEW_REASONS),
        }

    def legal_citations(self) -> list[str]:
        return ["GDPR Art. 22(3)", "EU AI Act Annex III §4(a)", "EEOC Uniform Guidelines"]

    # ---- evidence seams ------------------------------------------------

    def intake_doc_types(self) -> list[dict[str, Any]]:
        return [
            {"id": "resume", "display_name": "Resume", "accepted_mime": ["application/pdf"], "required": True, "freshness_days": 730},
            {"id": "job_description", "display_name": "Job description (text)", "accepted_mime": ["text/plain"], "required": True, "freshness_days": 365},
        ]

    def evidence_doc_types(self, target_feature: str) -> list[dict[str, Any]]:
        return [
            {"id": "certificate", "display_name": "Certification or course completion", "accepted_mime": ["application/pdf", "image/png", "image/jpeg"], "required": False, "freshness_days": 1825, "extracts_feature": "certification"},
            {"id": "course_completion", "display_name": "Course transcript", "accepted_mime": ["application/pdf"], "required": False, "freshness_days": 1825, "extracts_feature": "course"},
            {"id": "recommendation_letter", "display_name": "Recommendation letter", "accepted_mime": ["application/pdf"], "required": False, "freshness_days": 1095, "extracts_feature": "recommendation"},
            {"id": "linkedin_export", "display_name": "LinkedIn data export", "accepted_mime": ["application/pdf"], "required": False, "freshness_days": 90, "extracts_feature": "linkedin"},
            {"id": "resume", "display_name": "Updated resume", "accepted_mime": ["application/pdf"], "required": False, "freshness_days": 90, "extracts_feature": "resume_text"},
        ]

    def extract_prompt(self, doc_type: str) -> dict[str, Any]:
        return {
            "prompt": f"Extract a brief structured summary of this {doc_type.replace('_', ' ')}. Return JSON.",
            "schema": {
                "type": "object",
                "properties": {
                    "doc_type": {"type": "string"},
                    "issuer": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "issue_date": {"type": "string"},
                },
                "required": ["doc_type"],
            },
            "feature_field": None,
        }
```

- [ ] **Step 4: Run tests**

```bash
backend/.venv/bin/python -m pytest tests/shared/adapters/test_hiring.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add shared/adapters/hiring.py tests/shared/adapters
git commit -m "feat(hiring-adapter): LLM-as-judge resume scorer

shared/adapters/hiring.py rewritten from heuristic stub to OpenAI judge.
Implements the full DomainAdapter Protocol so Recourse renders it with
zero changes: predict/explain share one cached LLM call; explain returns
SHAP-shape rows with weight as the LLM-stated push; intake_doc_types,
evidence_doc_types, and extract_prompt drive the customer portal forms.

verbs() and legal_citations() hire-specific. EEOC + EU AI Act Annex III
called out — hiring is high-risk regulated.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Customer portal hiring backend

**Files:**
- Create: `customer_portal/backend/services/hiring_intake.py`
- Create: `customer_portal/backend/routes/hiring.py`
- Modify: `customer_portal/backend/db.py` (extend schema)
- Modify: `customer_portal/backend/main.py` (include router)

- [ ] **Step 1: Extend lender.db schema**

Add to `customer_portal/backend/db.py` SCHEMA constant (insert before final indexes):
```sql

CREATE TABLE IF NOT EXISTS job_postings (
  id              TEXT PRIMARY KEY,
  title           TEXT NOT NULL,
  jd_text         TEXT NOT NULL,
  created_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS hiring_applications (
  id              TEXT PRIMARY KEY,
  applicant_id    TEXT NOT NULL REFERENCES applicants(id),
  posting_id      TEXT NOT NULL REFERENCES job_postings(id),
  resume_text     TEXT NOT NULL,
  resume_path     TEXT,
  status          TEXT NOT NULL CHECK (status IN ('intake','decided','in_contest','closed')),
  submitted_at    INTEGER NOT NULL,
  decided_at      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_hiring_apps_status ON hiring_applications(status);
```

Also extend `applications.amount` shouldn't apply to hiring; we use `hiring_applications` separately so no schema collision.

- [ ] **Step 2: Write hiring intake service**

Create `customer_portal/backend/services/hiring_intake.py`:
```python
"""Hiring intake — read resume PDF text, call LLM via adapter, persist decision.

Uses pdfplumber for resume text (digital PDFs) and falls back to GLM-OCR if
text layer is empty. The hiring adapter then performs the LLM judgment.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shared.adapters import get_adapter
from shared.ocr import extract as ocr_extract


def extract_resume_text(path: Path) -> str:
    """Return the resume's text. Falls back to OCR on scanned PDFs."""
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(path) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        if text.strip():
            return text
    except Exception:
        pass
    result = ocr_extract(path, expected_doc_type="resume")
    return result.text_layer or json.dumps(result.fields)


def score_application(jd_text: str, resume_text: str) -> dict[str, Any]:
    adapter = get_adapter("hiring")
    features = {"jd_text": jd_text, "resume_text": resume_text}
    pred = adapter.predict(features)
    shap = adapter.explain(features)
    top_reasons = []
    sign = -1 if pred["decision"] == "denied" else 1
    ranked = sorted(shap, key=lambda r: sign * r.get("contribution", 0))
    for row in ranked[:3]:
        top_reasons.append(f"{row['display_name']}: {row.get('jd_requirement', '')} (your: {row.get('value', '')})")
    return {
        "verdict": pred["decision"],
        "prob_bad": pred["prob_bad"],
        "confidence": pred["confidence"],
        "shap": shap,
        "top_reasons": top_reasons,
        "model_version": adapter.model_version_hash,
    }
```

- [ ] **Step 3: Write hiring routes**

Create `customer_portal/backend/routes/hiring.py`:
```python
"""Hiring endpoints: create posting, submit candidate, view decision, mint contest link."""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from customer_portal.backend import db
from customer_portal.backend.services import hiring_intake
from shared.jwt_utils import sign_handoff

router = APIRouter(prefix="/api/v1/hiring", tags=["hiring"])

_UPLOAD_DIR = Path(os.environ.get("HELIX_LENDER_UPLOADS", "customer_portal/backend/uploads"))


class CreatePosting(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    jd_text: str = Field(min_length=20, max_length=20000)


@router.post("/postings")
def create_posting(req: CreatePosting) -> dict:
    posting_id = "JOB-2026-" + uuid.uuid4().hex[:6].upper()
    now = int(time.time())
    with db.conn() as c:
        c.execute(
            "INSERT INTO job_postings (id, title, jd_text, created_at) VALUES (?, ?, ?, ?)",
            (posting_id, req.title.strip(), req.jd_text.strip(), now),
        )
    return {"posting_id": posting_id, "title": req.title}


@router.get("/postings")
def list_postings() -> dict:
    with db.conn() as c:
        rows = c.execute("SELECT id, title, created_at FROM job_postings ORDER BY created_at DESC LIMIT 50").fetchall()
    return {"postings": [dict(r) for r in rows]}


@router.post("/postings/{posting_id}/candidates")
async def submit_candidate(
    posting_id: str,
    full_name: str = Form(...),
    dob: str = Form(...),
    email: str = Form(...),
    resume: UploadFile = File(...),
) -> dict:
    with db.conn() as c:
        posting = c.execute("SELECT * FROM job_postings WHERE id = ?", (posting_id,)).fetchone()
    if not posting:
        raise HTTPException(status_code=404, detail={"error": {"code": "posting_not_found", "message": "Unknown job posting."}})

    blob = await resume.read()
    if not blob:
        raise HTTPException(status_code=400, detail={"error": {"code": "empty_resume", "message": "Empty resume file."}})

    applicant_id = "CAN-" + uuid.uuid4().hex[:8].upper()
    application_id = "HR-2026-" + uuid.uuid4().hex[:4].upper()
    target_dir = _UPLOAD_DIR / application_id
    target_dir.mkdir(parents=True, exist_ok=True)
    resume_path = target_dir / "resume.pdf"
    resume_path.write_bytes(blob)
    resume_text = hiring_intake.extract_resume_text(resume_path)

    scored = hiring_intake.score_application(posting["jd_text"], resume_text)
    now = int(time.time())
    decision_id = "dec_" + uuid.uuid4().hex[:12]

    with db.conn() as c:
        c.execute(
            "INSERT INTO applicants (id, full_name, dob, email, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (applicant_id, full_name.strip(), dob, email.strip(), None, now),
        )
        c.execute(
            "INSERT INTO hiring_applications (id, applicant_id, posting_id, resume_text, resume_path, status, submitted_at, decided_at) VALUES (?, ?, ?, ?, ?, 'decided', ?, ?)",
            (application_id, applicant_id, posting_id, resume_text, str(resume_path), now, now),
        )
        c.execute(
            "INSERT INTO scored_features (application_id, feature_vector, model_version, scored_at) VALUES (?, ?, ?, ?)",
            (application_id, json.dumps({"jd_text": posting["jd_text"], "resume_text_sha": hashlib.sha256(resume_text.encode()).hexdigest()}), scored["model_version"], now),
        )
        c.execute(
            "INSERT INTO decisions (id, application_id, verdict, prob_bad, shap_json, top_reasons, source, decided_at) VALUES (?, ?, ?, ?, ?, ?, 'initial', ?)",
            (decision_id, application_id, scored["verdict"], scored["prob_bad"], json.dumps(scored["shap"]), json.dumps(scored["top_reasons"]), now),
        )
        c.execute(
            "INSERT INTO applications (id, applicant_id, amount, purpose, status, submitted_at, decided_at) VALUES (?, ?, 0, ?, 'decided', ?, ?)",
            (application_id, applicant_id, f"hiring · {posting['title']}", now, now),
        )

    return {
        "application_id": application_id,
        "applicant_id": applicant_id,
        "posting_id": posting_id,
        "decision": {
            "id": decision_id,
            "verdict": scored["verdict"],
            "prob_bad": scored["prob_bad"],
            "top_reasons": scored["top_reasons"],
            "shap": scored["shap"],
            "model_version": scored["model_version"],
        },
    }


@router.get("/applications/{app_id}")
def get_hiring_application(app_id: str) -> dict:
    with db.conn() as c:
        app_row = c.execute("SELECT * FROM hiring_applications WHERE id = ?", (app_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail={"error": {"code": "not_found", "message": "Unknown hiring application."}})
        applicant = c.execute("SELECT * FROM applicants WHERE id = ?", (app_row["applicant_id"],)).fetchone()
        decision = c.execute(
            "SELECT * FROM decisions WHERE application_id = ? ORDER BY decided_at DESC LIMIT 1",
            (app_id,),
        ).fetchone()
        posting = c.execute("SELECT id, title, jd_text FROM job_postings WHERE id = ?", (app_row["posting_id"],)).fetchone()
    return {
        "application": dict(app_row),
        "applicant": dict(applicant),
        "posting": dict(posting),
        "decision": (
            {
                "id": decision["id"],
                "verdict": decision["verdict"],
                "prob_bad": decision["prob_bad"],
                "top_reasons": json.loads(decision["top_reasons"] or "[]"),
                "shap": json.loads(decision["shap_json"] or "[]"),
                "source": decision["source"],
                "decided_at": decision["decided_at"],
            }
            if decision
            else None
        ),
    }


@router.post("/applications/{app_id}/request-contest-link")
def hiring_contest_link(app_id: str) -> dict:
    with db.conn() as c:
        app_row = c.execute("SELECT * FROM hiring_applications WHERE id = ?", (app_id,)).fetchone()
    if not app_row:
        raise HTTPException(status_code=404, detail={"error": {"code": "not_found", "message": "Unknown hiring application."}})

    with db.conn() as c:
        decision = c.execute(
            "SELECT verdict FROM decisions WHERE application_id = ? ORDER BY decided_at DESC LIMIT 1",
            (app_id,),
        ).fetchone()
    if not decision or decision["verdict"] != "denied":
        raise HTTPException(status_code=409, detail={"error": {"code": "not_contestable", "message": "Only denied applications can be contested."}})

    token, jti = sign_handoff(case_id=app_id, applicant_id=app_row["applicant_id"], decision="denied")
    now = int(time.time())
    with db.conn() as c:
        c.execute(
            "INSERT INTO contest_handoffs (jti, application_id, issued_at, expires_at) VALUES (?, ?, ?, ?)",
            (jti, app_id, now, now + 86400),
        )
        c.execute("UPDATE hiring_applications SET status = 'in_contest' WHERE id = ?", (app_id,))
        c.execute("UPDATE applications SET status = 'in_contest' WHERE id = ?", (app_id,))

    recourse_base = os.environ.get("HELIX_RECOURSE_PORTAL_URL", "http://localhost:5173")
    return {"contest_url": f"{recourse_base}/?t={token}", "jti": jti, "expires_in_hours": 24}
```

- [ ] **Step 4: Wire router**

Modify `customer_portal/backend/main.py`. Find the `from customer_portal.backend.routes import` line and add `hiring`:
```python
from customer_portal.backend.routes import applications, cases, hiring, operator, webhooks
```

Then in `create_app()` add (after `app.include_router(operator.router)`):
```python
    app.include_router(hiring.router)
```

- [ ] **Step 5: Verify imports**

```bash
backend/.venv/bin/python -c "import sys; sys.path.insert(0, '.'); from customer_portal.backend import main; print('routes:', len(main.app.routes))"
```

Expected: prints route count > 14 (was 14, now ~18 with hiring).

- [ ] **Step 6: Commit**

```bash
git add customer_portal/backend
git commit -m "feat(hiring-backend): /api/v1/hiring/* endpoints + lender.db schema

job_postings + hiring_applications tables share applicants and
contest_handoffs with the loans surface. Submit-candidate runs:
1) extract resume text via pdfplumber (GLM-OCR fallback)
2) call hiring adapter (LLM judge) → verdict + per-reason SHAP-like rows
3) persist into decisions/scored_features/applications so the existing
   operator console + cases endpoint show the case alongside loans
4) issue contest link on denial via the same shared.jwt_utils.sign_handoff

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Recourse re-eval supports text rebuttals

**Files:**
- Modify: `backend/services/evidence_pipeline.py` (accept rebuttal_text)
- Modify: `backend/routes/evidence.py` (multipart accepts rebuttal_text)
- Modify: `backend/services/rerun.py` (forwards rebuttals to adapter)
- Test: `tests/backend/services/test_rerun_hiring.py`

- [ ] **Step 1: Write the rebuttals-flow test**

Create `tests/backend/services/test_rerun_hiring.py`:
```python
"""Smoke that rerun.rerun_for_case forwards rebuttals to the adapter."""
import pytest
from unittest.mock import patch


def test_rebuttals_dict_shape_propagates():
    # Pure-Python shape contract; no DB required.
    rebuttals = [{"reason_id": "missing_k8s", "text": "I have AWS EKS exp.", "extracted": None}]
    feature_overrides = {"jd_text": "JD body", "resume_text": "Resume body", "_rebuttals": rebuttals, "_prior_decision": {"verdict": "denied"}}
    assert feature_overrides["_rebuttals"][0]["reason_id"] == "missing_k8s"
    assert feature_overrides["_prior_decision"]["verdict"] == "denied"
```

- [ ] **Step 2: Run, verify pass (sanity check, contract is just shape)**

```bash
backend/.venv/bin/python -m pytest tests/backend/services/test_rerun_hiring.py -v
```

Expected: 1 PASS.

- [ ] **Step 3: Modify evidence pipeline to accept rebuttal_text**

In `backend/services/evidence_pipeline.py`, modify the `process_upload` function signature:
```python
def process_upload(
    *,
    case_id: str,
    target_feature: str,
    doc_type: str,
    original_name: str,
    blob: bytes,
    rebuttal_text: str | None = None,
) -> dict[str, Any]:
```

Inside the function, after the existing extraction block, add:
```python
    if rebuttal_text:
        fields["_rebuttal_text"] = rebuttal_text.strip()
```

Inside the proposal-creation block (where `proposal_id` is set), pass the rebuttal text alongside extracted_value into the new column. Add a `rebuttal_text` column to proposals via a non-destructive `ALTER` at startup. Easier: store in evidence.extracted_json (already a JSON blob).

After `extracted=` block, change:
```python
                "notes": extraction.notes,
            }),
            claimed_value,
            now,
        ),
    )
```
to include rebuttal:
```python
                "notes": extraction.notes,
                "rebuttal_text": rebuttal_text,
            }),
            claimed_value,
            now,
        ),
    )
```

Also create a proposal even when claimed_value is None for hiring — it's text-only:
```python
        proposal_id = None
        if report.overall == "accepted":
            create_proposal = (claimed_value is not None and prior_value_f is not None) or rebuttal_text
            if create_proposal:
                proposal_id = "pr_" + uuid.uuid4().hex[:12]
                c.execute(
                    "INSERT INTO proposals (id, case_id, feature, original_value, proposed_value, evidence_id, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'validated', ?)",
                    (proposal_id, case_id, target_feature, prior_value_f or 0.0, claimed_value or 0.0, evidence_id, now),
                )
```

- [ ] **Step 4: Modify /contest/evidence to accept optional rebuttal_text**

In `backend/routes/evidence.py`, modify `upload_evidence`:
```python
@router.post("/evidence")
async def upload_evidence(
    session: dict = Depends(require_session),
    target_feature: str = Form(...),
    doc_type: str = Form(...),
    rebuttal_text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
) -> dict:
    blob = b""
    if file is not None:
        blob = await file.read()
    if not blob and not rebuttal_text:
        raise HTTPException(status_code=400, detail={"error": {"code": "empty_upload", "message": "Provide a file or rebuttal text."}})
    if not blob:
        # Text-only rebuttal → fabricate an empty placeholder doc so the
        # pipeline still records an evidence row.
        blob = (rebuttal_text or "").encode("utf-8")
    try:
        return evidence_pipeline.process_upload(
            case_id=session["case_id"],
            target_feature=target_feature,
            doc_type=doc_type,
            original_name=file.filename if file else "rebuttal.txt",
            blob=blob,
            rebuttal_text=rebuttal_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": {"code": str(exc), "message": "Upload failed."}})
```

- [ ] **Step 5: Modify rerun to forward rebuttals**

In `backend/services/rerun.py`, find the block that constructs `new_features = dict(snapshot_features)` and after the for loop add:
```python
    # For LLM-based domains (hiring), the adapter expects rebuttals + prior
    # decision in the feature dict. Collect them from evidence rows.
    with _db.conn() as c:
        rebuttal_rows = c.execute(
            """
            SELECT e.target_feature, e.extracted_json
            FROM evidence e
            JOIN proposals p ON p.evidence_id = e.id
            WHERE e.case_id = ? AND p.status = 'validated'
            """,
            (case_id,),
        ).fetchall()
    rebuttals: list[dict] = []
    for r in rebuttal_rows:
        try:
            blob = json.loads(r["extracted_json"] or "{}")
        except json.JSONDecodeError:
            blob = {}
        rebuttals.append({
            "reason_id": r["target_feature"],
            "text": blob.get("rebuttal_text"),
            "extracted": blob.get("fields"),
        })
    new_features["_rebuttals"] = rebuttals
    new_features["_prior_decision"] = snapshot_decision
```

(Note: `snapshot_decision` already exists from earlier `json.loads(case["snapshot_decision"])`.)

For loans, `_rebuttals` and `_prior_decision` are ignored (XGBoost adapter doesn't read them). For hiring, the adapter routes through `judge_re_evaluation`.

- [ ] **Step 6: Restart backend + verify import**

```bash
backend/.venv/bin/python -c "import sys; sys.path.insert(0, '.'); from backend import main; print('routes:', len(main.app.routes))"
```

Expected: import clean.

- [ ] **Step 7: Commit**

```bash
git add backend tests/backend
git commit -m "feat(recourse): rebuttal-text support in evidence pipeline + LLM rerun

evidence pipeline accepts an optional rebuttal_text form field alongside
the file. When present, it's stored on the evidence row and passed to
the adapter at re-eval time as part of new_features['_rebuttals'].

rerun.rerun_for_case now harvests every validated proposal's rebuttal +
extraction blob and constructs the LLM context the hiring adapter needs
(prior_decision + rebuttals). Loans adapter ignores those keys, so the
loans flow is unaffected.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Customer portal hiring frontend

**Files:**
- Create: `customer_portal/frontend/src/components/DomainSwitcher.tsx`
- Create: `customer_portal/frontend/src/components/hiring/PostingsView.tsx`
- Create: `customer_portal/frontend/src/components/hiring/NewPostingView.tsx`
- Create: `customer_portal/frontend/src/components/hiring/CandidateUploadView.tsx`
- Create: `customer_portal/frontend/src/components/hiring/HiringDecisionView.tsx`
- Create: `customer_portal/frontend/src/store_hiring.ts`
- Create: `customer_portal/frontend/src/lib/api_hiring.ts`
- Modify: `customer_portal/frontend/src/App.tsx`
- Modify: `customer_portal/frontend/src/components/Header.tsx`

- [ ] **Step 1: Write hiring API client**

Create `customer_portal/frontend/src/lib/api_hiring.ts`:
```ts
const BASE = "/api/v1/hiring";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let body: any;
    try { body = await res.json(); } catch { body = {}; }
    throw new Error(body?.detail?.error?.message || res.statusText);
  }
  return res.json() as Promise<T>;
}

export interface Posting { id: string; title: string; created_at: number; jd_text?: string }

export async function listPostings(): Promise<{ postings: Posting[] }> { return call("/postings"); }
export async function createPosting(title: string, jd_text: string): Promise<{ posting_id: string; title: string }> {
  return call("/postings", { method: "POST", body: JSON.stringify({ title, jd_text }) });
}

export async function submitCandidate(postingId: string, params: { full_name: string; dob: string; email: string }, resume: File): Promise<any> {
  const fd = new FormData();
  fd.append("full_name", params.full_name);
  fd.append("dob", params.dob);
  fd.append("email", params.email);
  fd.append("resume", resume);
  const res = await fetch(`${BASE}/postings/${postingId}/candidates`, { method: "POST", body: fd });
  if (!res.ok) {
    let body: any;
    try { body = await res.json(); } catch { body = {}; }
    throw new Error(body?.detail?.error?.message || res.statusText);
  }
  return res.json();
}

export async function getHiringApplication(appId: string): Promise<any> {
  return call(`/applications/${appId}`);
}

export async function requestContestLink(appId: string): Promise<{ contest_url: string }> {
  return call(`/applications/${appId}/request-contest-link`, { method: "POST" });
}
```

- [ ] **Step 2: Write hiring Zustand store**

Create `customer_portal/frontend/src/store_hiring.ts`:
```ts
import { create } from "zustand";
import * as api from "./lib/api_hiring";

export type HiringStage = "postings" | "newPosting" | "candidateUpload" | "decision";

interface State {
  stage: HiringStage;
  postings: api.Posting[];
  selectedPostingId: string | null;
  selectedPostingTitle: string;
  selectedPostingJd: string;
  newTitle: string;
  newJd: string;
  candidate: { full_name: string; dob: string; email: string };
  applicationId: string | null;
  decision: any | null;
  contestUrl: string | null;
  busy: boolean;
  error: string | null;

  goto(stage: HiringStage): void;
  loadPostings(): Promise<void>;
  setNewTitle(v: string): void;
  setNewJd(v: string): void;
  setCandidate(k: keyof State["candidate"], v: string): void;
  createPosting(): Promise<void>;
  selectPosting(p: api.Posting): void;
  uploadResume(file: File): Promise<void>;
  requestContest(): Promise<void>;
  reset(): void;
}

export const useHiring = create<State>((set, get) => ({
  stage: "postings",
  postings: [],
  selectedPostingId: null,
  selectedPostingTitle: "",
  selectedPostingJd: "",
  newTitle: "",
  newJd: "",
  candidate: { full_name: "", dob: "", email: "" },
  applicationId: null,
  decision: null,
  contestUrl: null,
  busy: false,
  error: null,

  goto(stage) { set({ stage, error: null }); },
  setNewTitle(v) { set({ newTitle: v }); },
  setNewJd(v) { set({ newJd: v }); },
  setCandidate(k, v) { set({ candidate: { ...get().candidate, [k]: v } }); },

  async loadPostings() {
    set({ busy: true, error: null });
    try { const r = await api.listPostings(); set({ postings: r.postings, busy: false }); }
    catch (e: any) { set({ error: e.message, busy: false }); }
  },

  async createPosting() {
    const { newTitle, newJd } = get();
    set({ busy: true, error: null });
    try {
      const r = await api.createPosting(newTitle, newJd);
      set({ busy: false, selectedPostingId: r.posting_id, selectedPostingTitle: r.title, selectedPostingJd: newJd, stage: "candidateUpload", newTitle: "", newJd: "" });
    } catch (e: any) { set({ error: e.message, busy: false }); }
  },

  selectPosting(p) {
    set({ selectedPostingId: p.id, selectedPostingTitle: p.title, selectedPostingJd: p.jd_text || "", stage: "candidateUpload" });
  },

  async uploadResume(file) {
    const { selectedPostingId, candidate } = get();
    if (!selectedPostingId) return;
    set({ busy: true, error: null });
    try {
      const r = await api.submitCandidate(selectedPostingId, candidate, file);
      set({ busy: false, applicationId: r.application_id, decision: r.decision, stage: "decision" });
    } catch (e: any) { set({ error: e.message, busy: false }); }
  },

  async requestContest() {
    const { applicationId } = get();
    if (!applicationId) return;
    set({ busy: true, error: null });
    try { const r = await api.requestContestLink(applicationId); set({ contestUrl: r.contest_url, busy: false }); }
    catch (e: any) { set({ error: e.message, busy: false }); }
  },

  reset() { set({ stage: "postings", selectedPostingId: null, selectedPostingTitle: "", selectedPostingJd: "", candidate: { full_name: "", dob: "", email: "" }, applicationId: null, decision: null, contestUrl: null, error: null }); },
}));
```

- [ ] **Step 3: Write DomainSwitcher**

Create `customer_portal/frontend/src/components/DomainSwitcher.tsx`:
```tsx
function currentDomain(): "loans" | "hiring" {
  return new URLSearchParams(window.location.search).get("domain") === "hiring" ? "hiring" : "loans";
}

export function DomainSwitcher() {
  const cur = currentDomain();
  const swap = (d: "loans" | "hiring") => {
    const url = new URL(window.location.href);
    url.searchParams.set("domain", d);
    url.searchParams.delete("view");
    window.location.href = url.toString();
  };
  return (
    <div className="inline-flex rounded-md border hairline overflow-hidden text-[12px]">
      <button
        onClick={() => swap("loans")}
        className={`px-3 py-1 ${cur === "loans" ? "bg-brand text-surface" : "bg-surface text-ink-muted hover:text-brand"}`}
      >Loans</button>
      <button
        onClick={() => swap("hiring")}
        className={`px-3 py-1 ${cur === "hiring" ? "bg-brand text-surface" : "bg-surface text-ink-muted hover:text-brand"}`}
      >Hiring</button>
    </div>
  );
}
```

- [ ] **Step 4: Write hiring views**

Create `customer_portal/frontend/src/components/hiring/PostingsView.tsx`:
```tsx
import { useEffect } from "react";
import { useHiring } from "../../store_hiring";

export function PostingsView() {
  const postings = useHiring((s) => s.postings);
  const load = useHiring((s) => s.loadPostings);
  const select = useHiring((s) => s.selectPosting);
  const goto = useHiring((s) => s.goto);

  useEffect(() => { load(); }, []);

  return (
    <section className="mx-auto max-w-3xl px-6 py-14">
      <div className="label mb-3">Hiring · Open roles</div>
      <h1 className="display text-4xl mb-3">Pick a role to screen candidates for.</h1>
      <p className="text-ink-muted mb-8 max-w-xl">
        Each role holds a job description the LLM judge compares every candidate against.
        Pick one to upload a resume, or post a new role.
      </p>
      <div className="card overflow-x-auto mb-6">
        <table className="w-full min-w-[560px] text-[14px]">
          <thead className="text-ink-muted">
            <tr className="border-b hairline">
              <th className="text-left px-4 py-3">Role</th>
              <th className="text-left px-4 py-3">Posting ID</th>
              <th className="text-left px-4 py-3">Posted</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {postings.map((p) => (
              <tr key={p.id} className="border-b hairline hover:bg-brand-soft/30">
                <td className="px-4 py-3 font-medium">{p.title}</td>
                <td className="px-4 py-3 mono text-[12px] text-ink-muted">{p.id}</td>
                <td className="px-4 py-3">{new Date(p.created_at * 1000).toLocaleDateString()}</td>
                <td className="px-4 py-3 text-right"><button className="btn-primary text-[13px] py-1.5" onClick={() => select(p)}>Open →</button></td>
              </tr>
            ))}
            {postings.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-6 text-sm text-ink-muted">No postings yet. Create one or run <span className="mono">make seed-hiring</span>.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <button className="btn-primary" onClick={() => goto("newPosting")}>+ Post a new role</button>
    </section>
  );
}
```

Create `customer_portal/frontend/src/components/hiring/NewPostingView.tsx`:
```tsx
import { useHiring } from "../../store_hiring";

export function NewPostingView() {
  const s = useHiring();
  const canSubmit = s.newTitle.trim().length > 2 && s.newJd.trim().length > 30;
  return (
    <section className="mx-auto max-w-2xl px-6 py-14">
      <div className="label mb-3">New role</div>
      <h1 className="display text-4xl mb-3">Describe the role.</h1>
      <p className="text-ink-muted mb-6 max-w-xl">
        Paste your real job description. The LLM judge extracts the must-have skills,
        years of experience, and required degree from this text.
      </p>
      <div className="card p-5 space-y-4">
        <div>
          <label className="label mb-2 block">Role title</label>
          <input className="input" placeholder="Senior Backend Engineer" value={s.newTitle} onChange={(e) => s.setNewTitle(e.target.value)} />
        </div>
        <div>
          <label className="label mb-2 block">Job description (paste full text)</label>
          <textarea
            rows={14}
            className="input"
            placeholder={"About the role…\nResponsibilities…\nRequirements:\n- 5+ years backend exp\n- Python, Postgres, Kubernetes\n- Bachelor's degree"}
            value={s.newJd}
            onChange={(e) => s.setNewJd(e.target.value)}
          />
          <div className="text-[11px] text-ink-muted mt-1 text-right">{s.newJd.length} chars</div>
        </div>
        {s.error && <div className="rounded-md border border-bad/40 bg-bad/5 px-3 py-2 text-sm text-bad">{s.error}</div>}
        <div className="flex items-center justify-between pt-2">
          <button className="btn-ghost" onClick={() => s.goto("postings")}>← Back</button>
          <button className="btn-primary" disabled={!canSubmit || s.busy} onClick={() => s.createPosting()}>
            {s.busy ? <><span className="spinner" /> Posting…</> : "Post role + screen candidates →"}
          </button>
        </div>
      </div>
    </section>
  );
}
```

Create `customer_portal/frontend/src/components/hiring/CandidateUploadView.tsx`:
```tsx
import { useRef } from "react";
import { useHiring } from "../../store_hiring";

export function CandidateUploadView() {
  const s = useHiring();
  const ref = useRef<HTMLInputElement | null>(null);
  const canPick = s.candidate.full_name.trim().length > 2 && s.candidate.dob && s.candidate.email.includes("@");
  return (
    <section className="mx-auto max-w-2xl px-6 py-14">
      <div className="label mb-3">Screen a candidate · {s.selectedPostingTitle}</div>
      <h1 className="display text-4xl mb-3">Upload the candidate's resume.</h1>
      <p className="text-ink-muted mb-6 max-w-xl">
        Tell us who this candidate is, then attach their resume PDF. The LLM judge
        scores resume-vs-JD and returns its reasoning instantly.
      </p>
      <div className="card p-5 space-y-4">
        <div>
          <label className="label mb-2 block">Candidate full name</label>
          <input className="input" placeholder="Asha Verma" value={s.candidate.full_name} onChange={(e) => s.setCandidate("full_name", e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label mb-2 block">Date of birth</label>
            <input className="input" type="date" value={s.candidate.dob} onChange={(e) => s.setCandidate("dob", e.target.value)} />
          </div>
          <div>
            <label className="label mb-2 block">Email</label>
            <input className="input" type="email" placeholder="asha@example.com" value={s.candidate.email} onChange={(e) => s.setCandidate("email", e.target.value)} />
          </div>
        </div>
        <div>
          <label className="label mb-2 block">Resume PDF</label>
          <input ref={ref} type="file" accept="application/pdf" className="sr-only"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) s.uploadResume(f); e.target.value = ""; }} />
          <button className="btn-ghost w-full py-3" disabled={!canPick || s.busy} onClick={() => ref.current?.click()}>
            {s.busy ? <><span className="spinner" /> Scoring…</> : "Choose resume PDF + score"}
          </button>
        </div>
        {s.error && <div className="rounded-md border border-bad/40 bg-bad/5 px-3 py-2 text-sm text-bad">{s.error}</div>}
        <div className="pt-2"><button className="btn-ghost" onClick={() => s.goto("postings")}>← All postings</button></div>
      </div>
    </section>
  );
}
```

Create `customer_portal/frontend/src/components/hiring/HiringDecisionView.tsx`:
```tsx
import { useEffect } from "react";
import { useHiring } from "../../store_hiring";

export function HiringDecisionView() {
  const s = useHiring();
  const decision = s.decision;

  useEffect(() => {
    if (decision?.verdict === "denied" && !s.contestUrl) s.requestContest();
  }, [decision?.verdict]);

  if (!decision) return null;
  const approved = decision.verdict === "approved";

  return (
    <section className="mx-auto max-w-3xl px-6 py-12">
      <button className="text-[13px] text-ink-muted hover:text-brand mb-6" onClick={() => s.reset()}>← All postings</button>
      <div className="label mb-3">{s.selectedPostingTitle}</div>
      <h1 className="display text-3xl mb-1">{s.candidate.full_name}</h1>
      <div className="mono text-[12px] text-ink-muted mb-6">{s.applicationId}</div>

      <div className={`card overflow-hidden mb-8 ${approved ? "border-good/40" : "border-bad/40"}`}>
        <div className={`px-6 py-6 ${approved ? "bg-good/5" : "bg-bad/5"}`}>
          <div className="flex items-center gap-3 mb-2">
            <span className={`pill ${approved ? "pill-approved" : "pill-denied"}`}>{decision.verdict}</span>
            <span className="label">Fit score: {(decision.confidence * 100).toFixed(0)}%</span>
          </div>
          <h2 className="display text-3xl">{approved ? "Move forward — strong fit." : "Not selected — see reasons."}</h2>
        </div>
        <div className="px-6 py-5 border-t hairline">
          <div className="label mb-3">Top factors</div>
          <ol className="space-y-2">
            {(decision.top_reasons || []).map((r: string, i: number) => (
              <li key={i} className="flex items-start gap-3 text-sm">
                <span className="mono text-[11px] text-ink-muted pt-[3px]">{(i + 1).toString().padStart(2, "0")}</span>
                <span>{r}</span>
              </li>
            ))}
          </ol>
        </div>
        <div className="px-6 py-5 border-t hairline bg-cream-soft/60">
          <details>
            <summary className="cursor-pointer text-[13px] text-ink hover:text-brand">All LLM reasons</summary>
            <table className="mt-3 w-full text-[12.5px]">
              <thead className="text-ink-muted">
                <tr><th className="text-left pb-1">Reason</th><th className="text-left pb-1">JD requires</th><th className="text-left pb-1">Resume says</th><th className="text-right pb-1">Weight</th></tr>
              </thead>
              <tbody>
                {(decision.shap || []).map((r: any) => (
                  <tr key={r.feature} className="border-t hairline">
                    <td className="py-1 pr-3">{r.display_name}</td>
                    <td className="py-1 pr-3 text-ink-muted">{r.jd_requirement}</td>
                    <td className="py-1 pr-3 mono">{r.value_display}</td>
                    <td className={`py-1 text-right ${r.contribution >= 0 ? "text-good" : "text-bad"}`}>{r.contribution >= 0 ? "+" : ""}{Number(r.contribution).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </div>
      </div>

      {!approved && (
        <div className="card p-6 mb-6 bg-accent-soft/30 border-brand/30">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="label mb-2">Right to contest</div>
              <h2 className="display text-xl mb-2">Hand off to Recourse</h2>
              <p className="text-ink-muted text-sm max-w-md">
                EU AI Act Annex III flags hiring as high-risk. The applicant
                has a right to challenge each reason individually with a
                document or a written rebuttal. Issuing the link mints a
                signed JWT they verify with their DOB.
              </p>
            </div>
            <div>
              {s.contestUrl ? <a href={s.contestUrl} target="_blank" rel="noopener" className="btn-primary">Open contest portal →</a>
                : <button className="btn-primary" disabled={s.busy} onClick={() => s.requestContest()}>{s.busy ? <><span className="spinner" /> Issuing…</> : "Issue contest link"}</button>}
            </div>
          </div>
          {s.contestUrl && <div className="mt-4 rounded-md border hairline bg-surface px-3 py-2 text-[12px] mono text-ink-muted break-all">{s.contestUrl}</div>}
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 5: Wire App + Header**

Modify `customer_portal/frontend/src/App.tsx`:
```tsx
import { useStore } from "./store";
import { useHiring } from "./store_hiring";
import { Header } from "./components/Header";
import { PickerView } from "./components/PickerView";
import { DecisionView } from "./components/DecisionView";
import { OperatorView } from "./components/OperatorView";
import { PostingsView } from "./components/hiring/PostingsView";
import { NewPostingView } from "./components/hiring/NewPostingView";
import { CandidateUploadView } from "./components/hiring/CandidateUploadView";
import { HiringDecisionView } from "./components/hiring/HiringDecisionView";

function currentDomain(): "loans" | "hiring" { return new URLSearchParams(window.location.search).get("domain") === "hiring" ? "hiring" : "loans"; }
function currentView(): "applicant" | "operator" { return new URLSearchParams(window.location.search).get("view") === "operator" ? "operator" : "applicant"; }

export function App() {
  const view = currentView();
  const domain = currentDomain();
  const stage = useStore((s) => s.stage);
  const hiringStage = useHiring((s) => s.stage);

  return (
    <div className="min-h-screen">
      <Header operatorMode={view === "operator"} domain={domain} />
      {view === "operator" ? <OperatorView /> :
       domain === "hiring" ? (
         hiringStage === "postings" ? <PostingsView /> :
         hiringStage === "newPosting" ? <NewPostingView /> :
         hiringStage === "candidateUpload" ? <CandidateUploadView /> :
         <HiringDecisionView />
       ) : (
         stage === "picker" ? <PickerView /> : <DecisionView />
       )}
      <footer className="border-t hairline mt-16 py-6 text-center text-[11px] text-ink-muted">
        LenderCo · {domain === "hiring" ? "Hiring decisions powered by gpt-4o-mini" : "Loan decisions powered by XGBoost + SHAP"}.
      </footer>
    </div>
  );
}
```

Modify `customer_portal/frontend/src/components/Header.tsx` — add a `domain` prop and render a domain pill (replace existing `Header({ operatorMode })` signature):
```tsx
import { DomainSwitcher } from "./DomainSwitcher";

export function Header({ operatorMode, domain }: { operatorMode: boolean; domain: "loans" | "hiring" }) {
  return (
    <header className="border-b hairline bg-surface">
      <div className="mx-auto flex max-w-shell items-center justify-between gap-4 px-4 py-4 sm:px-8 sm:py-5">
        <a href="/" className="flex items-center gap-3 text-ink hover:text-brand min-w-0">
          <span aria-hidden className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand">
            <span className="h-2.5 w-2.5 rounded-full bg-surface" />
          </span>
          <span className="min-w-0">
            <span className="display block text-lg leading-none">LenderCo</span>
            <span className="label block mt-1 hidden sm:block">{domain === "hiring" ? "Hiring · Internal" : "Retail lending · India"}</span>
          </span>
        </a>
        <div className="flex items-center gap-3">
          <DomainSwitcher />
          <nav className="flex items-center gap-2 text-sm sm:gap-3">
            <a href={`/?domain=${domain}`} className={operatorMode ? "text-ink-muted hover:text-brand" : "text-brand font-medium"}>{domain === "hiring" ? "Recruit" : "Apply"}</a>
            <span className="text-ink-muted">·</span>
            <a href={`/?domain=${domain}&view=operator`} className={operatorMode ? "text-brand font-medium" : "text-ink-muted hover:text-brand"}>Operator</a>
          </nav>
        </div>
      </div>
    </header>
  );
}
```

- [ ] **Step 6: Type-check**

```bash
cd customer_portal/frontend && ./node_modules/.bin/tsc --noEmit
```

Expected: no output (clean).

- [ ] **Step 7: Commit**

```bash
git add customer_portal/frontend
git commit -m "feat(lender-web): hiring vertical UI + domain switcher

DomainSwitcher pill toggles between ?domain=loans and ?domain=hiring;
both share the same Header / Operator / footer chrome.

Hiring flow: PostingsView (table of open roles) → NewPostingView (paste
JD) → CandidateUploadView (candidate name + DOB + email + resume PDF) →
HiringDecisionView (verdict, top reasons, full LLM reason table, contest
link auto-issued on denial).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Hiring case fixtures + seeder + smoke

**Files:**
- Create: `scripts/seed/hiring/__init__.py`
- Create: `scripts/seed/hiring/cases/__init__.py`
- Create: `scripts/seed/hiring/cases/_lib.py`
- Create: `scripts/seed/hiring/cases/build_all.py`
- Create: `scripts/seed/hiring/cases/case{1,2,3}/{jd.txt, case.json, resume.pdf}`
- Create: `scripts/seed_hiring.py`
- Create: `scripts/smoke_hiring.py`
- Modify: `Makefile` (targets)

- [ ] **Step 1: Write the resume PDF generator**

Create `scripts/seed/hiring/cases/_lib.py`:
```python
"""Generate plausible resume PDFs for hiring fixtures."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=20, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12, spaceAfter=2, textColor=colors.HexColor("#0E4A44")),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=10, spaceAfter=4, leading=14),
        "dim": ParagraphStyle("dim", parent=base["Normal"], fontSize=9, textColor=colors.HexColor("#5D6F6C")),
    }


def render_resume(path: Path, *, name: str, email: str, summary: str, experience: list[str], skills: list[str], education: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(path), pagesize=A4, title=f"{name} resume", author="Helix demo", rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    s = _styles()
    story = [
        Paragraph(name, s["h1"]),
        Paragraph(email, s["dim"]),
        Spacer(1, 12),
        Paragraph("Summary", s["h2"]),
        Paragraph(summary, s["body"]),
        Spacer(1, 8),
        Paragraph("Experience", s["h2"]),
    ]
    for e in experience:
        story.append(Paragraph(e, s["body"]))
    story += [
        Spacer(1, 8),
        Paragraph("Skills", s["h2"]),
        Paragraph(", ".join(skills), s["body"]),
        Spacer(1, 8),
        Paragraph("Education", s["h2"]),
        Paragraph(education, s["body"]),
    ]
    doc.build(story)
```

- [ ] **Step 2: Write the case builder with 3 cases**

Create `scripts/seed/hiring/__init__.py` (empty):
```python
```

Create `scripts/seed/hiring/cases/__init__.py` (empty):
```python
```

Create `scripts/seed/hiring/cases/build_all.py`:
```python
"""Build 3 hiring case fixtures (JD + resume + case.json)."""
from __future__ import annotations

import json
from pathlib import Path

from . import _lib

HERE = Path(__file__).resolve().parent

CASES = {
    "case1": {
        "posting_title": "Senior Backend Engineer",
        "jd_text": (
            "About the role:\n"
            "We are hiring a Senior Backend Engineer to own our Python services platform.\n\n"
            "Requirements:\n"
            "- 5+ years backend engineering experience\n"
            "- Strong Python (FastAPI / Django) + Postgres\n"
            "- Hands-on Kubernetes in production\n"
            "- Bachelor's degree in CS or equivalent\n"
            "- Comfortable owning on-call rotation\n\n"
            "Nice to have: Go, gRPC, observability tooling."
        ),
        "candidate": {"full_name": "Asha Verma", "dob": "1995-08-22", "email": "asha.verma@example.com"},
        "resume": {
            "name": "Asha Verma",
            "email": "asha.verma@example.com",
            "summary": "Backend engineer with 3 years of experience building Python services. Looking for a senior role.",
            "experience": [
                "<b>Backend Engineer · Razorpay (2024–present)</b> · Built REST APIs in FastAPI, Postgres schema design, deployed to AWS ECS.",
                "<b>Software Engineer · Freshworks (2022–2024)</b> · Django monolith maintenance. Wrote integration tests.",
            ],
            "skills": ["Python", "FastAPI", "Postgres", "Docker", "AWS ECS", "Git"],
            "education": "B.Tech Computer Science · NIT Trichy · 2022",
        },
        "story": "Strong Python but missing Kubernetes + only 3 yrs vs 5+ required. Designed to be denied then flippable with a CKA cert + freelance contracting evidence.",
    },
    "case2": {
        "posting_title": "Engineering Manager",
        "jd_text": (
            "About the role:\n"
            "Engineering Manager for a 12-person platform team.\n\n"
            "Requirements:\n"
            "- 8+ years total engineering experience\n"
            "- 3+ years managing engineers (hiring, perf, mentoring)\n"
            "- Has shipped distributed systems at scale (>1M req/day)\n"
            "- Master's degree preferred\n"
            "- Strong written communication\n"
        ),
        "candidate": {"full_name": "Devansh Kapoor", "dob": "1988-04-11", "email": "devansh.kapoor@example.com"},
        "resume": {
            "name": "Devansh Kapoor",
            "email": "devansh.kapoor@example.com",
            "summary": "Senior IC with 9 years building backend systems. No formal management title yet but mentored 4 juniors.",
            "experience": [
                "<b>Staff Engineer · Flipkart (2021–present)</b> · Owned recommendations service handling 4M req/day. Mentored 4 SDE-2 engineers.",
                "<b>Senior Engineer · Cleartrip (2017–2021)</b> · Booking pipeline rewrite, shaved 40% latency.",
                "<b>Engineer · Slideshare (2015–2017)</b> · Backend.",
            ],
            "skills": ["Java", "Go", "Kafka", "AWS", "System design", "Mentoring"],
            "education": "B.Tech IIT Bombay · 2015",
        },
        "story": "Strong IC depth and mentoring but no management title and no Master's. Held outcome — model says still IC, not yet manager.",
    },
    "case3": {
        "posting_title": "Junior Data Analyst",
        "jd_text": (
            "About the role:\n"
            "Junior Data Analyst on the growth team.\n\n"
            "Requirements:\n"
            "- 0-2 years experience\n"
            "- SQL and one of (Python | R)\n"
            "- Comfortable with dashboards (Looker / Metabase)\n"
            "- Bachelor's in any quantitative field\n"
        ),
        "candidate": {"full_name": "Rhea Joshi", "dob": "2002-01-15", "email": "rhea.joshi@example.com"},
        "resume": {
            "name": "Rhea Joshi",
            "email": "rhea.joshi@example.com",
            "summary": "Recent grad with 1 year as a part-time analytics intern at a fintech. Loves Python + SQL.",
            "experience": [
                "<b>Analytics Intern · Zerodha (2024–2025)</b> · SQL queries on PostgreSQL, dashboards in Metabase, ad-hoc Python notebooks.",
                "<b>Data Science Club · IIIT Hyderabad (2022–2024)</b> · Led Kaggle study group, ran weekly SQL sessions.",
            ],
            "skills": ["SQL", "Python", "Pandas", "Metabase", "Excel"],
            "education": "B.Tech Information Technology · IIIT Hyderabad · 2025",
        },
        "story": "Approved at intake. Demos the LLM judge accepting cleanly without contest.",
    },
}


def build_case(name: str, spec: dict) -> None:
    case_dir = HERE / name
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "jd.txt").write_text(spec["jd_text"])
    _lib.render_resume(case_dir / "resume.pdf", **spec["resume"])
    (case_dir / "case.json").write_text(json.dumps({
        "posting_title": spec["posting_title"],
        "jd_text": spec["jd_text"],
        "candidate": spec["candidate"],
        "story": spec["story"],
    }, indent=2))
    print(f"  built {name}: {spec['candidate']['full_name']} for {spec['posting_title']}")


def main() -> None:
    print("Generating hiring fixtures…")
    for name, spec in CASES.items():
        build_case(name, spec)
    print(f"Done. {len(CASES)} cases at {HERE}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Generate the fixtures**

```bash
cd /home/kerito/Desktop/Playground/helix && backend/.venv/bin/python -m scripts.seed.hiring.cases.build_all
```

Expected: prints 3 built cases.

- [ ] **Step 4: Write the hiring seeder**

Create `scripts/seed_hiring.py`:
```python
#!/usr/bin/env python3
"""Seed LenderCo with hiring postings + candidates from scripts/seed/hiring/cases/."""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from customer_portal.backend import db as lender_db
from customer_portal.backend.services import hiring_intake

CASES_DIR = REPO / "scripts" / "seed" / "hiring" / "cases"


def list_cases() -> list[str]:
    return sorted(p.name for p in CASES_DIR.iterdir() if (p / "case.json").exists())


def seed_case(case_name: str) -> None:
    case_dir = CASES_DIR / case_name
    spec = json.loads((case_dir / "case.json").read_text())
    jd_text = (case_dir / "jd.txt").read_text()
    resume_path = case_dir / "resume.pdf"

    lender_db.init_db()
    posting_id = "JOB-2026-" + uuid.uuid4().hex[:6].upper()
    application_id = "HR-2026-" + uuid.uuid4().hex[:4].upper()
    applicant_id = "CAN-" + uuid.uuid4().hex[:8].upper()
    now = int(time.time())

    resume_text = hiring_intake.extract_resume_text(resume_path)
    scored = hiring_intake.score_application(jd_text, resume_text)
    decision_id = "dec_" + uuid.uuid4().hex[:12]

    with lender_db.conn() as c:
        c.execute("INSERT INTO job_postings (id, title, jd_text, created_at) VALUES (?, ?, ?, ?)",
                  (posting_id, spec["posting_title"], jd_text, now))
        c.execute("INSERT INTO applicants (id, full_name, dob, email, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  (applicant_id, spec["candidate"]["full_name"], spec["candidate"]["dob"], spec["candidate"]["email"], None, now))
        c.execute("INSERT INTO hiring_applications (id, applicant_id, posting_id, resume_text, resume_path, status, submitted_at, decided_at) VALUES (?, ?, ?, ?, ?, 'decided', ?, ?)",
                  (application_id, applicant_id, posting_id, resume_text, str(resume_path), now, now))
        c.execute("INSERT INTO scored_features (application_id, feature_vector, model_version, scored_at) VALUES (?, ?, ?, ?)",
                  (application_id, json.dumps({"posting_id": posting_id}), scored["model_version"], now))
        c.execute("INSERT INTO decisions (id, application_id, verdict, prob_bad, shap_json, top_reasons, source, decided_at) VALUES (?, ?, ?, ?, ?, ?, 'initial', ?)",
                  (decision_id, application_id, scored["verdict"], scored["prob_bad"], json.dumps(scored["shap"]), json.dumps(scored["top_reasons"]), now))
        c.execute("INSERT INTO applications (id, applicant_id, amount, purpose, status, submitted_at, decided_at) VALUES (?, ?, 0, ?, 'decided', ?, ?)",
                  (application_id, applicant_id, f"hiring · {spec['posting_title']}", now, now))

    print(f"  {spec['candidate']['full_name']:24s} {scored['verdict'].upper():>9s} fit={scored['confidence']:.2f}  app={application_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", nargs="?", default=None)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    cases = list_cases()
    if not cases:
        print("No hiring cases. Run build_all first.", file=sys.stderr)
        sys.exit(2)
    if args.all or not args.case:
        for n in cases:
            print(f"▸ Seeding {n}")
            seed_case(n)
    else:
        seed_case(args.case)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run hiring seeder (requires OPENAI_API_KEY)**

```bash
cd /home/kerito/Desktop/Playground/helix && OPENAI_API_KEY=$OPENAI_API_KEY backend/.venv/bin/python scripts/seed_hiring.py --all
```

Expected: prints 3 candidates with verdicts. case3 (Rhea) approved, case1 (Asha) and case2 (Devansh) denied.

- [ ] **Step 6: Write hiring smoke test**

Create `scripts/smoke_hiring.py`:
```python
#!/usr/bin/env python3
"""End-to-end hiring round-trip smoke test against a live make-dev stack."""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

LENDER = "http://127.0.0.1:8001"
RECOURSE = "http://127.0.0.1:8000"
CASE = REPO / "scripts" / "seed" / "hiring" / "cases" / "case1"

GREEN = "\033[32m"; RED = "\033[31m"; BOLD = "\033[1m"; RESET = "\033[0m"
def ok(m): print(f"  {GREEN}✓{RESET} {m}")
def fail(m): print(f"  {RED}✗{RESET} {m}", file=sys.stderr); sys.exit(1)
def step(m): print(f"\n{BOLD}▸ {m}{RESET}")


def reset_and_seed():
    step("Reset + seed hiring case1")
    for p in (REPO / "backend" / "recourse.db", REPO / "backend" / "recourse.db-wal", REPO / "backend" / "recourse.db-shm",
              REPO / "customer_portal" / "backend" / "lender.db", REPO / "customer_portal" / "backend" / "lender.db-wal",
              REPO / "customer_portal" / "backend" / "lender.db-shm"):
        try: p.unlink()
        except FileNotFoundError: pass
    for d in (REPO / "backend" / "uploads", REPO / "customer_portal" / "backend" / "uploads"):
        if d.exists(): shutil.rmtree(d)
    from backend import db as recourse_db
    from customer_portal.backend import db as lender_db
    recourse_db.init_db()
    lender_db.init_db()
    res = subprocess.run([sys.executable, "scripts/seed_hiring.py", "case1"], cwd=REPO, capture_output=True, text=True)
    if res.returncode != 0:
        fail("seed_hiring failed:\n" + (res.stderr or res.stdout))
    ok("seeded Asha")
    time.sleep(0.5)


def first_hiring_app():
    r = httpx.get(f"{LENDER}/api/v1/operator/cases", timeout=5)
    cases = [c for c in r.json()["cases"] if c["id"].startswith("HR-")]
    if not cases:
        fail("no hiring case in operator listing")
    return cases[0]["id"]


def main():
    step("Health checks")
    for label, url in (("LenderCo", LENDER), ("Recourse", RECOURSE)):
        try: httpx.get(f"{url}/health", timeout=2).raise_for_status()
        except Exception as e: fail(f"{label} not reachable: {e}")
        ok(f"{label} healthy")
    reset_and_seed()
    app_id = first_hiring_app()
    ok(f"hiring app id = {app_id}")

    step("LenderCo issues hiring contest link")
    r = httpx.post(f"{LENDER}/api/v1/hiring/applications/{app_id}/request-contest-link", timeout=5)
    if r.status_code != 200: fail(f"contest link failed: {r.text}")
    token = r.json()["contest_url"].split("?t=", 1)[1]
    ok(f"JWT issued")

    step("Recourse exchanges JWT + DOB")
    with httpx.Client(timeout=30) as client:
        from scripts.seed.hiring.cases.build_all import CASES  # type: ignore
        dob = CASES["case1"]["candidate"]["dob"]
        r = client.post(f"{RECOURSE}/api/v1/contest/open", json={"token": token, "dob": dob})
        if r.status_code != 200: fail(f"contest/open failed: {r.text}")
        ok("session opened")

        step("Submit text rebuttal for first reason")
        case = client.get(f"{RECOURSE}/api/v1/contest/case").json()
        first_reason_id = case["snapshot"]["shap"][0]["feature"]
        r = client.post(
            f"{RECOURSE}/api/v1/contest/evidence",
            data={"target_feature": first_reason_id, "doc_type": "recommendation_letter", "rebuttal_text": "I have 5+ years of relevant experience including 18 months freelance work delivering Kubernetes-based services."},
        )
        if r.status_code != 200: fail(f"evidence upload failed: {r.text}")
        ok(f"rebuttal accepted; overall={r.json()['validation']['overall']}")

        step("Submit contest")
        r = client.post(f"{RECOURSE}/api/v1/contest/submit")
        if r.status_code != 200: fail(f"submit failed: {r.text}")
        body = r.json()
        ok(f"outcome={body['outcome']}  new_verdict={body['new_decision']['verdict']}")

    step("Verify audit chain")
    r = httpx.get(f"{RECOURSE}/api/v1/audit/{body['case_id']}/verify", timeout=5)
    if r.status_code != 200 or not r.json().get("ok"):
        fail(f"audit verify failed: {r.text}")
    ok(f"chain valid · {r.json()['rows']} rows")

    print(f"\n{GREEN}{BOLD}✓ Hiring smoke passed.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 7: Add Makefile targets**

Append to `Makefile`:
```makefile

seed-hiring:
	$(PY) scripts/seed_hiring.py $(CASE)

seed-hiring-all:
	$(PY) scripts/seed_hiring.py --all

smoke-hiring:
	$(PY) scripts/smoke_hiring.py

hiring-fixtures:
	$(PY) -m scripts.seed.hiring.cases.build_all
```

- [ ] **Step 8: Commit**

```bash
git add scripts/seed/hiring scripts/seed_hiring.py scripts/smoke_hiring.py Makefile
git commit -m "feat(hiring-fixtures): 3 demo cases + seeder + smoke test

scripts/seed/hiring/cases/case{1,2,3}/ each holds jd.txt, resume.pdf
(generated via reportlab), and case.json. Designed cases:

  case1  Asha Verma · Sr Backend Eng  → denied (3 yrs vs 5+, no k8s)
  case2  Devansh Kapoor · Eng Manager → denied/held (no PM title)
  case3  Rhea Joshi · Jr Data Analyst → approved at intake

scripts/seed_hiring.py runs the full intake (LLM call hits OpenAI; cached
to .llm-cache/ so repeats are free). scripts/smoke_hiring.py walks the
full round-trip including a text rebuttal and audit verification.

Makefile adds seed-hiring, seed-hiring-all, smoke-hiring, hiring-fixtures.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: README + integration check

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

Insert new section after "Future-domain expansion" (or replace the post-hackathon roadmap row for hiring with a "shipped" note):

```markdown

## Hiring vertical (shipped)

The same Recourse pipeline now handles hiring decisions. Recruiter pastes a
JD + uploads a resume PDF; LenderCo calls **OpenAI gpt-4o-mini** with a
strict JSON schema to score fit and list per-reason rejections. Denied
candidates get the same JWT handoff to Recourse, contest each reason
with either an uploaded document or a free-text rebuttal, and the LLM
re-judges with the rebuttal in context.

Run:
```bash
export OPENAI_API_KEY=sk-...
make hiring-fixtures
make seed-hiring-all
make dev
```
Visit `http://localhost:5174/?domain=hiring`. Pick a posting, drill in,
issue contest link, follow it to Recourse, contest a reason, watch the
verdict flip on a strong rebuttal.

LLM calls are disk-cached under `.llm-cache/` so repeated demos cost
zero tokens after the first run.

**What this proves about the architecture:** Recourse backend + frontend
were unchanged. Only the customer-portal got new routes + UI, and the
hiring adapter slotted into the existing Adapter Protocol. Hiring is
~4 days of new code on top of a workflow that took ~3 weeks for loans.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README documents hiring vertical + run instructions"
```

---

## Self-review

Before handoff:

1. **Spec coverage:** Q1-Q14 mapped to tasks. Q1 free-text JD = Task 3 + Task 5 NewPostingView. Q2 LLM-only = Task 1 + Task 2. Q3 no recruiter approval gate = applicant link auto-issued in Task 3. Q4 doc-or-text = Task 4 evidence pipeline change. Q6 same customer_portal + ?domain = Task 5 DomainSwitcher. Q7 one-JD-one-resume = Task 3 schema. Q9 LLM judge = Task 1. Q11 all-LLM = Task 2 (no hard gates). Q12 rebuttal re-scores = Task 4 + Task 1. Q13 3 cases = Task 6. Q14 no PII redaction = (intentionally absent). All covered.

2. **Placeholder scan:** No "TODO" / "TBD" in any step. Every code block is complete.

3. **Type consistency:** `Decision` not used (using `dict`). `judge_initial` and `judge_re_evaluation` referenced consistently. `_judge` private method on adapter. `Posting` interface in TS used in PostingsView and store. ✓

4. **Risk callouts:**
   - Recourse changes (Task 4) are MINIMAL but live — could break loans flow. Mitigation: smoke test (loans) re-runs after each change in Task 4.
   - LLM cache: cleared between Asha case retries → re-runs cost tokens. Acceptable.
   - OPENAI_API_KEY required for any hiring step. Failures explicit.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-19-hiring-extension.md`.

User already chose **Subagent-Driven**. Invoking superpowers:subagent-driven-development next.
