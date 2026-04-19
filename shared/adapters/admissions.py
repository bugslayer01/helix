from __future__ import annotations

from ._heuristic import HeuristicAdapter


def _gpa(v: float) -> str:
    return f"{float(v):.2f} / 4.00"


def _percentile(v: float) -> str:
    return f"{round(float(v))}th pct"


def _score10(v: float) -> str:
    return f"{float(v):.1f} / 10"


def _bool_first_gen(v: float) -> str:
    return "First-generation" if float(v) else "Continuing-generation"


class AdmissionsAdapter(HeuristicAdapter):
    domain_id = "admissions"
    display_name = "Admissions & scholarship"
    bias = -1.2

    form_key_map = {
        "gpa": "gpa",
        "test_score": "test_percentile",
        "extracurriculars": "extracurriculars_score",
        "essay": "essay_score",
        "recommendation": "recommendation_score",
        "first_gen": "first_gen_status",
        "region": "region_signal",
    }

    features = [
        {
            "feature": "gpa",
            "display_name": "Grade point average",
            "group": "academics",
            "baseline": 3.3,
            "scale": 0.4,
            "weight": 1.4,
            "direction": -1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "min": 0.0, "max": 4.0, "step": 0.01,
            "evidence_types": ["transcript_upload", "registrar_letter"],
            "hint": "Admitted students in this cohort typically present a GPA of 3.6+.",
            "placeholder": "e.g. 3.72",
            "display": _gpa,
            "unit": "/ 4.0",
            "approval_baseline": 3.7,
        },
        {
            "feature": "test_percentile",
            "display_name": "Standardised test percentile",
            "group": "academics",
            "baseline": 70.0,
            "scale": 15.0,
            "weight": 0.9,
            "direction": -1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "min": 0, "max": 100, "step": 1,
            "evidence_types": ["score_report"],
            "hint": "Admits in this programme tend to sit above the 80th percentile. Re-takes count.",
            "placeholder": "e.g. 88",
            "display": _percentile,
            "unit": "pct",
            "approval_baseline": 88,
        },
        {
            "feature": "extracurriculars_score",
            "display_name": "Extracurricular strength",
            "group": "profile",
            "baseline": 5.0,
            "scale": 2.0,
            "weight": 0.8,
            "direction": -1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "evidence_types": ["activity_log", "leadership_verification", "competition_record"],
            "hint": "Submit verified activity records; the score updates after verification.",
            "placeholder": "",
            "display": _score10,
            "unit": "/ 10",
            "approval_baseline": 7.5,
        },
        {
            "feature": "essay_score",
            "display_name": "Essay evaluation",
            "group": "profile",
            "baseline": 5.5,
            "scale": 1.5,
            "weight": 1.0,
            "direction": -1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "evidence_types": ["essay_resubmission", "writing_portfolio"],
            "hint": "Submit a revised essay; a reader re-scores before the model re-runs.",
            "placeholder": "",
            "display": _score10,
            "unit": "/ 10",
            "approval_baseline": 7.0,
        },
        {
            "feature": "recommendation_score",
            "display_name": "Recommendation strength",
            "group": "profile",
            "baseline": 6.0,
            "scale": 1.5,
            "weight": 0.6,
            "direction": -1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "evidence_types": ["replacement_recommendation"],
            "hint": "Provide a replacement recommendation; the referee verifies before the score updates.",
            "placeholder": "",
            "display": _score10,
            "unit": "/ 10",
            "approval_baseline": 8.0,
        },
        {
            "feature": "first_gen_status",
            "display_name": "First-generation status",
            "group": "about",
            "baseline": 0.0,
            "scale": 1.0,
            "weight": 0.0,
            "direction": 1,
            "contestable": False,
            "protected": True,
            "display": _bool_first_gen,
            "unit": "",
        },
        {
            "feature": "region_signal",
            "display_name": "Region",
            "group": "about",
            "baseline": 0.0,
            "scale": 1.0,
            "weight": 0.0,
            "direction": 1,
            "contestable": False,
            "protected": True,
            "display": lambda v: "—",
            "unit": "",
        },
    ]

    groups = [
        {
            "id": "about",
            "title": "About you",
            "locked": True,
            "locked_hint": "Protected attributes",
            "field_keys": ["first_gen_status", "region_signal"],
        },
        {
            "id": "academics",
            "title": "Academics",
            "locked": False,
            "field_keys": ["gpa", "test_percentile"],
        },
        {
            "id": "profile",
            "title": "Your profile",
            "locked": False,
            "field_keys": [
                "extracurriculars_score",
                "essay_score",
                "recommendation_score",
            ],
        },
    ]

    copy = {
        "subject_noun": "application",
        "approved_label": "Admitted",
        "denied_label": "Not offered",
        "hero_question": "Why weren't you offered a seat?",
        "hero_subtitle": (
            "The admissions model weighed several of your application signals. "
            "Here's how each moved the verdict — and which levers are fair to pull."
        ),
        "outcome_title_flipped": "Your admissions decision has changed.",
        "outcome_title_same": "The decision didn't change — but here's what moved.",
        "outcome_review_title": "Your case is with a reader.",
        "correction_title": "What looked wrong?",
        "correction_sub": "Flag anything on your application that was misread or should have been scored differently.",
        "new_evidence_title": "What can you add?",
        "new_evidence_sub": "Add updated transcripts, new test scores, or a replacement recommendation.",
        "review_title": "Ask for a human reader.",
        "review_sub": "A member of admissions will read your file. The automated score is not re-computed.",
        "correction_button": "Correct my application",
        "correction_body": "A score on your application was misapplied. Model re-runs on corrected values.",
        "new_evidence_body": "Add new transcripts, scores, or recommendations we didn't have.",
        "review_body": "Model is not re-run. A human admissions reader reviews the case.",
    }

    citations = ["GDPR Art. 22(3)", "FERPA", "US HEA §485"]

    custom_review_reasons = [
        {"value": "protected_attribute_bias", "label": "I believe a protected characteristic influenced scoring"},
        {"value": "rubric_misapplied", "label": "The rubric was misapplied to my application"},
        {"value": "holistic_review_needed", "label": "My case calls for holistic review, not automated scoring"},
        {"value": "other", "label": "Other"},
    ]
