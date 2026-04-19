from __future__ import annotations

from ._heuristic import HeuristicAdapter


def _velocity(v: float) -> str:
    n = round(float(v))
    return "0" if n == 0 else f"{n} in 24h"


def _score(v: float) -> str:
    return f"{round(float(v))}"


def _days(v: float) -> str:
    d = round(float(v))
    if d < 30:
        return f"{d} days"
    if d < 365:
        return f"{d // 30} months"
    return f"{d / 365:.1f} years"


def _amount(v: float) -> str:
    return f"₹{int(float(v)):,}"


def _bool(v: float) -> str:
    return "Yes" if float(v) else "No"


class FraudAdapter(HeuristicAdapter):
    domain_id = "fraud"
    display_name = "Account safety"
    bias = -1.0

    form_key_map = {
        "velocity": "transaction_velocity_24h",
        "geo_risk": "geo_risk_score",
        "device_trust": "device_trust_score",
        "account_age": "account_age_days",
        "amount": "largest_transaction_amount",
        "country_change": "country_change_24h",
        "ip_reputation": "ip_reputation_flag",
    }

    features = [
        {
            "feature": "transaction_velocity_24h",
            "display_name": "Transactions in last 24h",
            "group": "activity",
            "baseline": 3.0,
            "scale": 4.0,
            "weight": 1.0,
            "direction": 1,
            # Pulled straight from the transaction log — user can't edit it.
            # They can submit context (travel, bill run) that the model weighs.
            "contestable": True,
            "correction_policy": "evidence_driven",
            "evidence_types": ["calendar_excerpt", "travel_itinerary", "subscription_list"],
            "hint": "Submit context (a trip, a month-end bill run) and the velocity bump is re-weighted.",
            "placeholder": "",
            "display": _velocity,
            "unit": "",
            "approval_baseline": 3,
        },
        {
            "feature": "geo_risk_score",
            "display_name": "Geo-risk score",
            "group": "activity",
            "baseline": 20.0,
            "scale": 15.0,
            "weight": 1.1,
            "direction": 1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "evidence_types": ["travel_itinerary", "booking_confirmation"],
            "hint": "Attach travel documents; the geo-risk is cleared after verification.",
            "placeholder": "",
            "display": _score,
            "unit": "/100",
            "approval_baseline": 20,
        },
        {
            "feature": "device_trust_score",
            "display_name": "Device trust",
            "group": "device",
            "baseline": 70.0,
            "scale": 15.0,
            "weight": 0.9,
            "direction": -1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "evidence_types": ["id_verification", "two_factor_reconfirm"],
            "hint": "Pass ID verification or 2FA; trust rebuilds after validation.",
            "placeholder": "",
            "display": _score,
            "unit": "/100",
            "approval_baseline": 85,
        },
        {
            "feature": "account_age_days",
            "display_name": "Account age",
            "group": "device",
            "baseline": 180.0,
            "scale": 365.0,
            "weight": 0.5,
            "direction": -1,
            "contestable": False,
            "correction_policy": "locked",
            "evidence_types": [],
            "hint": "Older accounts get more benefit of the doubt. Not contestable — account-creation date is fixed.",
            "placeholder": "",
            "display": _days,
            "unit": "",
            "approval_baseline": 900,
        },
        {
            "feature": "largest_transaction_amount",
            "display_name": "Largest transaction (24h)",
            "group": "activity",
            "baseline": 30000.0,
            "scale": 50000.0,
            "weight": 0.9,
            "direction": 1,
            "contestable": True,
            # Actual ledger amount — user can't edit, but an invoice flips the
            # risk weighting to "expected high-value purchase".
            "correction_policy": "evidence_driven",
            "evidence_types": ["invoice", "merchant_confirmation"],
            "hint": "Attach an invoice or merchant confirmation; the amount is re-weighted as expected.",
            "placeholder": "",
            "display": _amount,
            "unit": "₹",
            "approval_baseline": 30000,
        },
        {
            "feature": "country_change_24h",
            "display_name": "Country changed in 24h",
            "group": "activity",
            "baseline": 0.0,
            "scale": 1.0,
            "weight": 0.7,
            "direction": 1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "evidence_types": ["travel_itinerary"],
            "hint": "Travel documents clear the cross-border trigger after validation.",
            "placeholder": "",
            "display": _bool,
            "unit": "",
            "approval_baseline": 0,
        },
        {
            "feature": "ip_reputation_flag",
            "display_name": "IP reputation flag",
            "group": "device",
            "baseline": 0.0,
            "scale": 1.0,
            "weight": 0.6,
            "direction": 1,
            "contestable": True,
            "correction_policy": "evidence_driven",
            "evidence_types": ["network_explanation"],
            "hint": "Submit a network explanation (office Wi-Fi / VPN / shared ISP) — flag is re-weighted on validation.",
            "placeholder": "",
            "display": _bool,
            "unit": "",
            "approval_baseline": 0,
        },
    ]

    groups = [
        {
            "id": "activity",
            "title": "Recent activity",
            "locked": False,
            "field_keys": [
                "transaction_velocity_24h",
                "geo_risk_score",
                "largest_transaction_amount",
                "country_change_24h",
            ],
        },
        {
            "id": "device",
            "title": "Your account & device",
            "locked": False,
            "field_keys": [
                "device_trust_score",
                "account_age_days",
                "ip_reputation_flag",
            ],
        },
    ]

    copy = {
        "subject_noun": "account",
        "approved_label": "Active",
        "denied_label": "Frozen",
        "hero_question": "Why was your account frozen?",
        "hero_subtitle": (
            "The fraud model scored a mix of recent-activity and device signals. "
            "Here's how each contributed to the freeze decision."
        ),
        "outcome_title_flipped": "Your account has been reinstated.",
        "outcome_title_same": "The freeze stands — here's what we re-evaluated.",
        "outcome_review_title": "A fraud analyst is reviewing your account.",
        "correction_title": "What does the model have wrong?",
        "correction_sub": "Flag signals that don't match reality — wrong velocity, wrong geo, wrong device state.",
        "new_evidence_title": "What can you attach?",
        "new_evidence_sub": "Travel itineraries, merchant invoices, or a completed 2FA challenge usually resolve these.",
        "review_title": "Talk to a fraud analyst.",
        "review_sub": "A human analyst will read your case. The classifier is not re-run.",
        "correction_button": "Correct the signals",
        "correction_body": "Something in the signals doesn't match reality. Model re-runs on corrected signals.",
        "new_evidence_body": "Add travel documents, invoices, or 2FA results.",
        "review_body": "Classifier is not re-run. A fraud analyst reviews the case.",
    }

    citations = ["GDPR Art. 22(3)", "DPDP §11", "RBI Master Directions on Fraud"]

    custom_review_reasons = [
        {"value": "false_positive_trip", "label": "The model flagged legitimate travel or a known purchase"},
        {"value": "shared_device", "label": "A household member's activity tripped the model"},
        {"value": "protected_attribute_bias", "label": "I believe profiling rather than activity drove the freeze"},
        {"value": "other", "label": "Other"},
    ]
