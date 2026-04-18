from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np

from ._shared import (
    UNIVERSAL_CONTEST_REASONS,
    UNIVERSAL_REVIEW_REASONS,
    file_sha256,
    load_json,
)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
METADATA_DIR = MODELS_DIR / "metadata"

FEATURE_ORDER = [
    "RevolvingUtilizationOfUnsecuredLines",
    "age",
    "NumberOfTime30-59DaysPastDueNotWorse",
    "DebtRatio",
    "MonthlyIncome",
    "NumberOfOpenCreditLinesAndLoans",
    "NumberOfTimes90DaysLate",
    "NumberRealEstateLoansOrLines",
    "NumberOfTime60-89DaysPastDueNotWorse",
    "NumberOfDependents",
]

DISPLAY_NAMES = {
    "RevolvingUtilizationOfUnsecuredLines": "Credit card use",
    "age": "Age",
    "NumberOfTime30-59DaysPastDueNotWorse": "30–59 days late",
    "DebtRatio": "Debt-to-income ratio",
    "MonthlyIncome": "Monthly income",
    "NumberOfOpenCreditLinesAndLoans": "Open credit lines",
    "NumberOfTimes90DaysLate": "90+ days late",
    "NumberRealEstateLoansOrLines": "Home / property loans",
    "NumberOfTime60-89DaysPastDueNotWorse": "60–89 days late",
    "NumberOfDependents": "People depending on you",
}

FORM_KEY_MAP = {
    "debt_ratio": "DebtRatio",
    "income": "MonthlyIncome",
    "revolving": "RevolvingUtilizationOfUnsecuredLines",
    "credit_lines": "NumberOfOpenCreditLinesAndLoans",
    "real_estate_loans": "NumberRealEstateLoansOrLines",
    "late_30_59": "NumberOfTime30-59DaysPastDueNotWorse",
    "late_60_89": "NumberOfTime60-89DaysPastDueNotWorse",
    "late_90_plus": "NumberOfTimes90DaysLate",
    "age": "age",
    "dependents": "NumberOfDependents",
}

DISPLAY_VALUE = {
    "RevolvingUtilizationOfUnsecuredLines": lambda v: f"{round(float(v) * 100)}%",
    "DebtRatio": lambda v: f"{round(float(v) * 100)}%",
    "MonthlyIncome": lambda v: f"₹{int(v):,}",
    "NumberOfTime30-59DaysPastDueNotWorse": lambda v: "Never" if int(v) == 0 else f"{int(v)} time" + ("s" if int(v) != 1 else ""),
    "NumberOfTime60-89DaysPastDueNotWorse": lambda v: "Never" if int(v) == 0 else f"{int(v)} time" + ("s" if int(v) != 1 else ""),
    "NumberOfTimes90DaysLate": lambda v: "Never" if int(v) == 0 else f"{int(v)} time" + ("s" if int(v) != 1 else ""),
    "age": lambda v: f"{int(v)}",
    "NumberOfDependents": lambda v: f"{int(v)}",
    "NumberOfOpenCreditLinesAndLoans": lambda v: f"{int(v)}",
    "NumberRealEstateLoansOrLines": lambda v: f"{int(v)}",
}


class LoansAdapter:
    domain_id = "loans"
    display_name = "Loan application"

    def __init__(self) -> None:
        self._model_path = MODELS_DIR / "loans.pkl"
        self._explainer_path = MODELS_DIR / "loans_explainer.pkl"
        self._meta = load_json(METADATA_DIR / "loans.json", {"contestability": {}})
        self._hints = load_json(METADATA_DIR / "loans_hints.json", {})
        self._medians = load_json(METADATA_DIR / "loans_medians.json", {})
        self.model_version_hash = file_sha256(self._model_path)
        self._model = joblib.load(self._model_path) if self._model_path.exists() else None
        self._explainer = joblib.load(self._explainer_path) if self._explainer_path.exists() else None

    # ---- prediction -----------------------------------------------------

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        features = self._normalize(features)
        x = self._vector(features)
        if self._model is not None:
            prob_bad = float(self._model.predict_proba(x)[0, 1])
        else:
            prob_bad = _heuristic_prob_bad(features)
        approved = prob_bad < 0.5
        return {
            "decision": "approved" if approved else "denied",
            "confidence": round(1.0 - prob_bad, 4),
            "prob_bad": round(prob_bad, 4),
        }

    def explain(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        features = self._normalize(features)
        x = self._vector(features)
        if self._explainer is not None:
            raw = np.asarray(self._explainer.shap_values(x))[0]
        else:
            raw = np.zeros(len(FEATURE_ORDER))
        # flip sign so "positive = pushes toward approval"
        contributions = -raw
        meta = self._meta.get("contestability", {})
        rows: list[dict[str, Any]] = []
        for i, name in enumerate(FEATURE_ORDER):
            m = meta.get(name, {})
            display = DISPLAY_VALUE.get(name, lambda v: str(v))(features.get(name, 0) or 0)
            rows.append(
                {
                    "feature": name,
                    "display_name": DISPLAY_NAMES[name],
                    "value": features.get(name),
                    "value_display": display,
                    "contribution": float(round(contributions[i], 4)),
                    "contestable": bool(m.get("contestable", True)),
                    "protected": bool(m.get("protected", False)),
                }
            )
        return rows

    def feature_schema(self) -> list[dict[str, Any]]:
        meta = self._meta.get("contestability", {})
        schema: list[dict[str, Any]] = []
        for name in FEATURE_ORDER:
            m = meta.get(name, {})
            protected = bool(m.get("protected", False))
            contestable = bool(m.get("contestable", True))
            # Every loan feature is computed from authoritative paperwork
            # (pay stubs, credit reports, loan payoff receipts). We never let
            # the user type a number — they hand over the document and the
            # validator extracts the resulting value.
            policy = "locked" if protected or not contestable else "evidence_driven"
            schema.append(
                {
                    "feature": name,
                    "form_key": _reverse_map(FORM_KEY_MAP).get(name, name.lower()),
                    "display_name": DISPLAY_NAMES[name],
                    "group": _group_for(name),
                    "contestable": contestable,
                    "protected": protected,
                    "correction_policy": policy,
                    "evidence_types": list(m.get("evidence_types", [])),
                    "unit": _unit_for(name),
                    "hint": _hint_for(name),
                    "hint_placeholder": _placeholder_for(name),
                    "min": _bounds_for(name)[0],
                    "max": _bounds_for(name)[1],
                    "step": _step_for(name),
                    "realistic_delta_multiplier": float(
                        m.get("realistic_delta_multiplier", 3.0)
                    ),
                }
            )
        return schema

    def suggest_counterfactual(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        case_id = features.get("_case_id")
        if case_id and case_id in self._hints:
            return list(self._hints[case_id])
        out: list[dict[str, Any]] = []
        for name, median in self._medians.items():
            current = features.get(name)
            if current is None or abs(float(current) - float(median)) < 1e-6:
                continue
            ev = self._meta.get("contestability", {}).get(name, {}).get("evidence_types", ["supporting_document"])
            out.append(
                {
                    "feature": name,
                    "evidence_type": ev[0] if ev else "supporting_document",
                    "target_value_hint": round(float(median), 4),
                    "source": "approved_median",
                }
            )
        return out[:3]

    def verbs(self) -> dict[str, str]:
        return {
            "subject_noun": "loan application",
            "approved_label": "Approved",
            "denied_label": "Denied",
            "hero_question": "Why were you denied?",
            "hero_subtitle": (
                "The model weighed several of your financial signals against "
                "each other. Here's how each factor moved the verdict."
            ),
            "outcome_title_flipped": "The decision has changed.",
            "outcome_title_same": "The decision didn't change — but here's what moved.",
            "outcome_review_title": "Your case is with a reviewer.",
            "correction_title": "What was wrong?",
            "correction_sub": "Flag the information you believe is incorrect, enter the right value, and tell us how you'd prove it.",
            "new_evidence_title": "What's changed?",
            "new_evidence_sub": "Attach updated documentation for any factor that's no longer accurate.",
            "review_title": "Tell a person what went wrong.",
            "review_sub": "A human reviewer will read your case — the model is not re-run.",
            "correction_button": "Correct existing information",
            "correction_body": "Some data used in the decision was wrong. Model re-runs on corrected values.",
            "new_evidence_body": "Circumstances have changed or you have documents not provided before.",
            "review_body": "Model is not re-run. Case is routed to a person for review.",
        }

    def profile_groups(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "about",
                "title": "About you",
                "locked": True,
                "locked_hint": "Not used to decide",
                "field_keys": ["age", "NumberOfDependents"],
            },
            {
                "id": "money",
                "title": "Money in & money out",
                "locked": False,
                "field_keys": [
                    "MonthlyIncome",
                    "DebtRatio",
                    "RevolvingUtilizationOfUnsecuredLines",
                ],
            },
            {
                "id": "open",
                "title": "What's open",
                "locked": False,
                "field_keys": [
                    "NumberOfOpenCreditLinesAndLoans",
                    "NumberRealEstateLoansOrLines",
                ],
            },
            {
                "id": "history",
                "title": "Missed payments (last 2 yrs)",
                "locked": False,
                "field_keys": [
                    "NumberOfTime30-59DaysPastDueNotWorse",
                    "NumberOfTime60-89DaysPastDueNotWorse",
                    "NumberOfTimes90DaysLate",
                ],
            },
        ]

    def path_reasons(self) -> dict[str, list[dict[str, str]]]:
        return {
            "contest": list(UNIVERSAL_CONTEST_REASONS),
            "review": list(UNIVERSAL_REVIEW_REASONS),
        }

    def legal_citations(self) -> list[str]:
        return ["GDPR Art. 22(3)", "DPDP §11", "FCRA §615"]

    # ---- internals ------------------------------------------------------

    @staticmethod
    def _normalize(features: dict[str, Any]) -> dict[str, Any]:
        """Accept form-keyed or model-keyed input, return model-keyed."""
        out = dict(features)
        for form_key, model_key in FORM_KEY_MAP.items():
            if form_key in features and model_key != form_key:
                value = features[form_key]
                try:
                    v = float(value)
                    if model_key in (
                        "DebtRatio",
                        "RevolvingUtilizationOfUnsecuredLines",
                    ) and v > 1:
                        v = v / 100.0
                    out[model_key] = v
                except (TypeError, ValueError):
                    pass
        return out

    @staticmethod
    def _vector(features: dict[str, Any]) -> np.ndarray:
        return np.array(
            [[float(features.get(k, 0) or 0) for k in FEATURE_ORDER]],
            dtype=float,
        )


def _reverse_map(m: dict[str, str]) -> dict[str, str]:
    return {v: k for k, v in m.items()}


def _group_for(name: str) -> str:
    if name in ("age", "NumberOfDependents"):
        return "about"
    if name in ("MonthlyIncome", "DebtRatio", "RevolvingUtilizationOfUnsecuredLines"):
        return "money"
    if name in ("NumberOfOpenCreditLinesAndLoans", "NumberRealEstateLoansOrLines"):
        return "open"
    return "history"


def _unit_for(name: str) -> str:
    if name == "MonthlyIncome":
        return "₹/month"
    if name in ("DebtRatio", "RevolvingUtilizationOfUnsecuredLines"):
        return "%"
    return ""


def _hint_for(name: str) -> str:
    return {
        "RevolvingUtilizationOfUnsecuredLines": "Approved applicants typically have credit card use below 30%.",
        "DebtRatio": "Approved applicants typically have debt-to-income below 31%.",
        "MonthlyIncome": "Typical approvals show monthly income above ₹55,000.",
        "NumberOfTime30-59DaysPastDueNotWorse": "Even a single late payment moves the model sharply toward denial.",
    }.get(name, "")


def _placeholder_for(name: str) -> str:
    return {
        "RevolvingUtilizationOfUnsecuredLines": "e.g. 25",
        "DebtRatio": "e.g. 28",
        "MonthlyIncome": "e.g. 55000",
        "NumberOfTime30-59DaysPastDueNotWorse": "e.g. 0",
    }.get(name, "")


def _bounds_for(name: str) -> tuple[float | None, float | None]:
    """(min, max) inclusive bounds for user-submitted corrections."""
    return {
        "RevolvingUtilizationOfUnsecuredLines": (0.0, 100.0),
        "DebtRatio": (0.0, 100.0),
        "MonthlyIncome": (0.0, 10_000_000.0),
        "NumberOfOpenCreditLinesAndLoans": (0.0, 50.0),
        "NumberRealEstateLoansOrLines": (0.0, 20.0),
        "NumberOfTime30-59DaysPastDueNotWorse": (0.0, 30.0),
        "NumberOfTime60-89DaysPastDueNotWorse": (0.0, 30.0),
        "NumberOfTimes90DaysLate": (0.0, 30.0),
        "age": (18.0, 110.0),
        "NumberOfDependents": (0.0, 20.0),
    }.get(name, (None, None))


def _step_for(name: str) -> float:
    return {
        "RevolvingUtilizationOfUnsecuredLines": 1.0,
        "DebtRatio": 1.0,
        "MonthlyIncome": 100.0,
    }.get(name, 1.0)


def _heuristic_prob_bad(features: dict[str, Any]) -> float:
    debt = float(features.get("DebtRatio", 0.4) or 0.4)
    income = float(features.get("MonthlyIncome", 30000) or 30000)
    late_30 = float(features.get("NumberOfTime30-59DaysPastDueNotWorse", 0) or 0)
    late_90 = float(features.get("NumberOfTimes90DaysLate", 0) or 0)
    score = 2.2 * (debt - 0.31) + 0.9 * late_30 + 2.4 * late_90 - 0.5 * (income / 60000)
    return float(1.0 / (1.0 + np.exp(-score)))
