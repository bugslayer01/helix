from __future__ import annotations

from ._heuristic import HeuristicAdapter


def _days(v: float) -> str:
    d = round(float(v))
    if d < 30:
        return f"{d} days"
    if d < 365:
        return f"{d // 30} months"
    years = d / 365
    return f"{years:.1f} years"


def _bool(v: float) -> str:
    return "Yes" if float(v) else "No"


def _score(v: float) -> str:
    return f"{round(float(v))}"


def _count(v: float) -> str:
    n = round(float(v))
    return "None" if n == 0 else f"{n}"


class ModerationAdapter(HeuristicAdapter):
    domain_id = "moderation"
    display_name = "Content moderation"
    bias = -1.4

    form_key_map = {
        "policy_match": "policy_match_score",
        "account_age": "account_age_days",
        "reports": "report_count",
        "strikes": "history_strikes",
        "post_length": "post_length_chars",
        "verified": "account_verified",
        "region": "region_signal",
    }

    features = [
        {
            "feature": "policy_match_score",
            "display_name": "Policy-match score",
            "group": "post",
            "baseline": 30.0,
            "scale": 20.0,
            "weight": 2.2,
            "direction": 1,
            "contestable": True,
            # The score is always recomputed from post text + context — the
            # user submits explanation/satire-label/news-source and the
            # classifier re-runs. They can never type a new number.
            "correction_policy": "evidence_driven",
            "evidence_types": ["context_explanation", "satire_label", "news_source_link"],
            "hint": "Add context (satire/news citation/explanation) — the classifier re-scores on the merged post.",
            "placeholder": "",
            "display": _score,
            "unit": "/100",
            "approval_baseline": 20,
        },
        {
            "feature": "account_age_days",
            "display_name": "Account age",
            "group": "account",
            "baseline": 90.0,
            "scale": 365.0,
            "weight": 0.5,
            "direction": -1,
            "contestable": False,      # objective fact, not contestable in Path 1
            "correction_policy": "locked",
            "evidence_types": [],
            "hint": "Derived from your account creation date — not contestable.",
            "placeholder": "",
            "display": _days,
            "unit": "",
            "approval_baseline": 730,
        },
        {
            "feature": "report_count",
            "display_name": "Reports from other users",
            "group": "post",
            "baseline": 0.0,
            "scale": 5.0,
            "weight": 1.1,
            "direction": 1,
            "contestable": True,
            # Individual reports can be contested as coordinated; the classifier
            # down-weights affected reports on its own.
            "correction_policy": "evidence_driven",
            "evidence_types": ["coordinated_report_evidence", "report_dispute"],
            "hint": "Attach evidence of coordinated reporting; flagged reports are down-weighted.",
            "placeholder": "",
            "display": _count,
            "unit": "",
            "approval_baseline": 0,
        },
        {
            "feature": "history_strikes",
            "display_name": "Prior policy strikes",
            "group": "account",
            "baseline": 0.0,
            "scale": 2.0,
            "weight": 0.9,
            "direction": 1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "evidence_types": ["appeal_record", "strike_expiry_proof"],
            "hint": "Provide an appeal-record or expiry proof; old strikes are expunged automatically.",
            "placeholder": "",
            "display": _count,
            "unit": "",
            "approval_baseline": 0,
        },
        {
            "feature": "post_length_chars",
            "display_name": "Post length",
            "group": "post",
            "baseline": 400.0,
            "scale": 500.0,
            "weight": 0.2,
            "direction": -1,
            "contestable": False,      # objective — reads straight from the post
            "correction_policy": "locked",
            "evidence_types": [],
            "hint": "Derived from the post itself — not contestable.",
            "placeholder": "",
            "display": lambda v: f"{round(float(v))} chars",
            "unit": "chars",
            "approval_baseline": 600,
        },
        {
            "feature": "account_verified",
            "display_name": "Account verification",
            "group": "account",
            "baseline": 0.0,
            "scale": 1.0,
            "weight": 0.8,
            "direction": -1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "evidence_types": ["identity_verification", "public_figure_confirmation"],
            "hint": "Complete ID verification to flip this. The value updates only when verification completes.",
            "placeholder": "",
            "display": _bool,
            "unit": "",
            "approval_baseline": 1,
        },
        {
            "feature": "region_signal",
            "display_name": "Region metadata",
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
            "title": "Creator metadata",
            "locked": True,
            "locked_hint": "Not used to decide",
            "field_keys": ["region_signal"],
        },
        {
            "id": "post",
            "title": "This post",
            "locked": False,
            "field_keys": [
                "policy_match_score",
                "report_count",
                "post_length_chars",
            ],
        },
        {
            "id": "account",
            "title": "Your account",
            "locked": False,
            "field_keys": [
                "account_age_days",
                "history_strikes",
                "account_verified",
            ],
        },
    ]

    copy = {
        "subject_noun": "post",
        "approved_label": "Published",
        "denied_label": "Removed",
        "hero_question": "Why was your post removed?",
        "hero_subtitle": (
            "The moderation model scored this post against our policies. "
            "Here's how each signal moved the removal decision."
        ),
        "outcome_title_flipped": "Your post has been reinstated.",
        "outcome_title_same": "The removal stands — but here's what we re-evaluated.",
        "outcome_review_title": "A human moderator is reviewing your post.",
        "correction_title": "What got misread?",
        "correction_sub": "Flag signals the automated system misinterpreted — missing context, coordinated reporting, stale strikes.",
        "new_evidence_title": "What context can you add?",
        "new_evidence_sub": "Add satire labels, news-source citations, or a verification that wasn't present when we first moderated.",
        "review_title": "Tell a moderator what they missed.",
        "review_sub": "A human moderator will re-read your post. The classifier is not re-run.",
        "correction_button": "Correct the signals",
        "correction_body": "The moderation signals misread your post. Model re-runs on corrected signals.",
        "new_evidence_body": "Add context, citations, or identity proof the classifier didn't see.",
        "review_body": "Classifier is not re-run. A human moderator reviews the case.",
    }

    citations = ["DSA Art. 17", "DSA Art. 23", "GDPR Art. 22(3)"]

    custom_review_reasons = [
        {"value": "missing_context", "label": "The automated system missed context (satire, news, cultural reference)"},
        {"value": "coordinated_reporting", "label": "I believe reports against me were coordinated"},
        {"value": "protected_speech", "label": "This is protected speech / journalism"},
        {"value": "policy_disagreement", "label": "I disagree with the policy itself"},
        {"value": "other", "label": "Other"},
    ]
