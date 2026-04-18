"""Multi-domain seed applicant profiles + prefix-based lookup.

Reference prefix → domain:
    RC-*   loans
    HR-*   hiring
    CM-*   content moderation
    UA-*   university admissions
    FR-*   fraud / account freeze
"""

from __future__ import annotations

from typing import Any


SEED_CASES: dict[str, dict[str, Any]] = {
    # ---- loans -----------------------------------------------------------
    "A4F2-9E31": {
        "application_reference": "RC-2024-A4F2-9E31",
        "date_of_birth": "1990-03-12",
        "applicant_name": "Priya Sharma",
        "domain": "loans",
        "features": {
            "RevolvingUtilizationOfUnsecuredLines": 0.68,
            "age": 34,
            "NumberOfTime30-59DaysPastDueNotWorse": 1,
            "DebtRatio": 0.42,
            "MonthlyIncome": 45200,
            "NumberOfOpenCreditLinesAndLoans": 8,
            "NumberOfTimes90DaysLate": 0,
            "NumberRealEstateLoansOrLines": 1,
            "NumberOfTime60-89DaysPastDueNotWorse": 0,
            "NumberOfDependents": 2,
        },
    },
    # ---- hiring ----------------------------------------------------------
    "H7K2-4B19": {
        "application_reference": "HR-2024-H7K2-4B19",
        "date_of_birth": "1995-07-22",
        "applicant_name": "Ananya Kulkarni",
        "domain": "hiring",
        "features": {
            "years_experience": 3.0,
            "education_level": 2,
            "skill_match_score": 58,
            "employment_gap_months": 9,
            "referral": 0,
            "age": 29,
            "gender_signal": 1,
        },
    },
    # ---- content moderation ---------------------------------------------
    "C3M8-8F44": {
        "application_reference": "CM-2024-C3M8-8F44",
        "date_of_birth": "1998-11-05",
        "applicant_name": "Kabir Das",
        "domain": "moderation",
        "features": {
            "policy_match_score": 68,
            "account_age_days": 820,
            "report_count": 14,
            "history_strikes": 1,
            "post_length_chars": 220,
            "account_verified": 0,
            "region_signal": 1,
        },
    },
    # ---- university admissions ------------------------------------------
    "U6A1-2D77": {
        "application_reference": "UA-2024-U6A1-2D77",
        "date_of_birth": "2006-02-18",
        "applicant_name": "Rohan Pillai",
        "domain": "admissions",
        "features": {
            "gpa": 3.08,
            "test_percentile": 62,
            "extracurriculars_score": 3.8,
            "essay_score": 4.6,
            "recommendation_score": 5.5,
            "first_gen_status": 1,
            "region_signal": 1,
        },
    },
    # ---- fraud -----------------------------------------------------------
    "F9B5-7E21": {
        "application_reference": "FR-2024-F9B5-7E21",
        "date_of_birth": "1988-05-30",
        "applicant_name": "Arjun Rao",
        "domain": "fraud",
        "features": {
            "transaction_velocity_24h": 9,
            "geo_risk_score": 65,
            "device_trust_score": 42,
            "account_age_days": 2200,
            "largest_transaction_amount": 180000,
            "country_change_24h": 1,
            "ip_reputation_flag": 1,
        },
    },
}


def find_case(application_reference: str, date_of_birth: str) -> dict[str, Any] | None:
    """Locate a seed case by (reference, DOB)."""
    needle_ref = application_reference.strip().upper()
    needle_dob = date_of_birth.strip()
    for case_id, data in SEED_CASES.items():
        if (
            data["application_reference"].upper() == needle_ref
            and data["date_of_birth"] == needle_dob
        ):
            return {"case_id": case_id, **data}
    return None


def cases_by_domain() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for case_id, data in SEED_CASES.items():
        out.setdefault(data["domain"], []).append({"case_id": case_id, **data})
    return out


DEMO_SAFE_CASE_IDS: set[str] = set(SEED_CASES.keys())
