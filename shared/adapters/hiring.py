"""Hiring adapter — LLM-as-judge using shared.llm.openai_judge.

Differs from loans (XGBoost): there is no fitted model file; the model is
GPT-4o-mini constrained by a JSON schema. predict() and explain() share a
single LLM call cached by prompt hash, so calling them in sequence on the
same features costs one round-trip.

The adapter expects ``features`` to contain ``jd_text`` and ``resume_text``
(strings). For re-evaluation, the contest pipeline injects ``_prior_decision``
(the cached initial-call output) and ``_rebuttals`` (a list of
``{reason_id, text?, extracted?}`` dicts) — see backend/services/rerun.py.
"""
from __future__ import annotations

from typing import Any

from shared.llm import openai_judge

from ._shared import UNIVERSAL_CONTEST_REASONS, UNIVERSAL_REVIEW_REASONS


class HiringAdapter:
    domain_id = "hiring"
    display_name = "Hiring decision"

    @property
    def model_version_hash(self) -> str:
        return openai_judge.model_version()

    # ---- prediction -----------------------------------------------------

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
        # Hiring features are emergent from each LLM call. The static schema
        # below covers only the base intake shape (one slot for the resume
        # itself). Per-reason contestable rows are surfaced at runtime via
        # explain() and rendered the same way as loans SHAP rows.
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
            "hero_subtitle": (
                "The recruiter's screening model compared your resume against the "
                "role's requirements. Here's its reasoning."
            ),
            "outcome_title_flipped": "Your application has moved forward.",
            "outcome_title_same": "The recruiter still has concerns.",
            "outcome_review_title": "A human reviewer is taking over.",
            "correction_title": "Counter the recruiter's reasoning.",
            "correction_sub": (
                "For each reason below, attach a document or write a rebuttal. "
                "The model re-judges with your input."
            ),
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
            {
                "id": "candidate",
                "title": "About this candidate",
                "locked": False,
                "field_keys": ["resume_text"],
            },
        ]

    def path_reasons(self) -> dict[str, list]:
        return {
            "contest": list(UNIVERSAL_CONTEST_REASONS),
            "review": list(UNIVERSAL_REVIEW_REASONS),
        }

    def legal_citations(self) -> list[str]:
        return ["GDPR Art. 22(3)", "EU AI Act Annex III 4(a)", "EEOC Uniform Guidelines"]

    # ---- evidence seams ------------------------------------------------

    def intake_doc_types(self) -> list[dict[str, Any]]:
        return [
            {"id": "resume", "display_name": "Resume", "accepted_mime": ["application/pdf"], "required": True, "freshness_days": 730},
            {"id": "job_description", "display_name": "Job description (text)", "accepted_mime": ["text/plain"], "required": True, "freshness_days": 365},
        ]

    def evidence_doc_types(self, target_feature: str) -> list[dict[str, Any]]:
        # Same set for every contestable reason; the recruiter's reason IDs
        # are emergent so we don't switch on target_feature here.
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
