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
            "Add it to your .env.local file or export it."
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
