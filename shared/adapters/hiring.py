from __future__ import annotations

from ._heuristic import HeuristicAdapter


def _years(v: float) -> str:
    y = round(float(v))
    return "New to work" if y == 0 else f"{y} yr" + ("" if y == 1 else "s")


def _months(v: float) -> str:
    m = round(float(v))
    return "No gap" if m == 0 else f"{m} month" + ("" if m == 1 else "s")


def _edu_label(v: float) -> str:
    n = round(float(v))
    return ["None", "High school", "Bachelors", "Masters", "PhD"][max(0, min(4, n))]


def _score(v: float) -> str:
    return f"{round(float(v))}"


def _bool_label(v: float) -> str:
    return "Yes" if float(v) else "No"


class HiringAdapter(HeuristicAdapter):
    domain_id = "hiring"
    display_name = "Job application"
    bias = -0.9

    form_key_map = {
        "years_experience": "years_experience",
        "education_level": "education_level",
        "skill_match": "skill_match_score",
        "employment_gap": "employment_gap_months",
        "referral": "referral",
        "age": "age",
        "gender": "gender_signal",
    }

    features = [
        {
            "feature": "years_experience",
            "display_name": "Years of relevant experience",
            "group": "experience",
            "baseline": 5.0,
            "scale": 3.0,
            "weight": 1.0,
            "direction": -1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "min": 0, "max": 60, "step": 1,
            "evidence_types": ["employment_letter", "linkedin_export", "reference_contact"],
            "hint": "Typical candidates selected for this role had 5+ years of relevant experience.",
            "placeholder": "e.g. 6",
            "display": _years,
            "unit": "years",
            "approval_baseline": 6,
        },
        {
            "feature": "education_level",
            "display_name": "Education level",
            "group": "experience",
            "baseline": 2.0,
            "scale": 1.0,
            "weight": 0.6,
            "direction": -1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "min": 0, "max": 4, "step": 1,
            "evidence_types": ["degree_certificate", "transcript"],
            "hint": "The role's profile expects at least a bachelor's degree or equivalent.",
            "placeholder": "e.g. 2 (Bachelors)",
            "display": _edu_label,
            "unit": "",
            "approval_baseline": 3,
        },
        {
            "feature": "skill_match_score",
            "display_name": "Skills match score",
            "group": "experience",
            "baseline": 65.0,
            "scale": 15.0,
            "weight": 1.3,
            "direction": -1,
            "contestable": True,
            # Evidence-driven: the score is recomputed from uploaded portfolios,
            # certifications, or contested resume highlights — not typed freely.
            "correction_policy": "evidence_driven",
            "evidence_types": ["portfolio_link", "certification", "contested_resume_highlight"],
            "hint": "Selected candidates typically score 70+. Upload a portfolio or certifications to trigger a rescore.",
            "placeholder": "",
            "display": _score,
            "unit": "/100",
            "approval_baseline": 80,
        },
        {
            "feature": "employment_gap_months",
            "display_name": "Recent employment gap",
            "group": "experience",
            "baseline": 3.0,
            "scale": 6.0,
            "weight": 0.7,
            "direction": 1,
            "contestable": True,
            # Gap is derived from the resume; user can submit an explanation
            # that the system validates and applies.
            "correction_policy": "evidence_driven",
            "evidence_types": ["explanation_letter", "caregiver_documentation"],
            "hint": "Gaps above 6 months weigh against candidates — an explanation letter can contextualise them.",
            "placeholder": "",
            "display": _months,
            "unit": "months",
            "approval_baseline": 0,
        },
        {
            "feature": "referral",
            "display_name": "Internal referral",
            "group": "experience",
            "baseline": 0.0,
            "scale": 1.0,
            "weight": 0.5,
            "direction": -1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "evidence_types": ["referral_confirmation"],
            "hint": "A referral is a positive signal but never a substitute for skill match.",
            "placeholder": "",
            "display": _bool_label,
            "unit": "",
            "approval_baseline": 1,
        },
        {
            "feature": "age",
            "display_name": "Age",
            "group": "about",
            "baseline": 35.0,
            "scale": 20.0,
            "weight": 0.0,
            "direction": 1,
            "contestable": False,
            "protected": True,
            "display": lambda v: f"{round(float(v))}",
            "unit": "",
        },
        {
            "feature": "gender_signal",
            "display_name": "Gender signal in resume",
            "group": "about",
            "baseline": 0.0,
            "scale": 1.0,
            "weight": 0.05,
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
            "locked_hint": "Not used to decide",
            "field_keys": ["age", "gender_signal"],
        },
        {
            "id": "experience",
            "title": "Experience & fit",
            "locked": False,
            "field_keys": [
                "years_experience",
                "education_level",
                "skill_match_score",
                "employment_gap_months",
                "referral",
            ],
        },
    ]

    copy = {
        "subject_noun": "job application",
        "approved_label": "Advanced",
        "denied_label": "Not selected",
        "hero_question": "Why weren't you selected?",
        "hero_subtitle": (
            "The model scored your profile against the role's rubric. "
            "Here's how each dimension moved the decision."
        ),
        "outcome_title_flipped": "The screening outcome has changed.",
        "outcome_title_same": "The outcome didn't change — but here's what moved.",
        "outcome_review_title": "Your application is with a human recruiter.",
        "correction_title": "What was wrong on your profile?",
        "correction_sub": "Flag fields that were misrepresented by your resume parse or scoring rubric.",
        "new_evidence_title": "What can you add?",
        "new_evidence_sub": "Attach credentials, certifications, or referral confirmations we didn't have before.",
        "review_title": "Tell a recruiter what happened.",
        "review_sub": "A human reviewer will read your case. The model is not re-run.",
        "correction_button": "Correct my profile",
        "correction_body": "Resume parsing missed something or a skill was mis-scored. Model re-runs on corrected values.",
        "new_evidence_body": "Add credentials or referrals the screening didn't see.",
        "review_body": "Model is not re-run. A human recruiter reviews the case.",
    }

    citations = ["GDPR Art. 22(3)", "EEOC Uniform Guidelines", "NYC Local Law 144"]

    custom_review_reasons = [
        {"value": "protected_attribute_bias", "label": "I believe a protected characteristic influenced screening"},
        {"value": "resume_parsing_error", "label": "The resume parser misread my profile"},
        {"value": "inappropriate_use_of_model", "label": "Automated screening isn't appropriate for my case"},
        {"value": "other", "label": "Other"},
    ]
