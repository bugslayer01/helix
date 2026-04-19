"""Train an XGBoost credit-risk classifier on a synthetic dataset.

Prefers the real Give Me Some Credit CSV at `data/cs-training.csv` if present.
Falls back to a synthetic generator calibrated to flag DebtRatio and
payment-history features, which is enough for the demo's SHAP story.

Running this script writes:
  models/loans.pkl            — the trained XGBoost booster (via joblib)
  models/loans_explainer.pkl  — a fitted shap.TreeExplainer
  models/metadata/loans_medians.json — approved-applicant medians per feature
  models/metadata/loans_hints.json   — pre-computed counterfactual hints per seed case

Run from the `backend/` directory:
    .venv/bin/python -m models.train_loans
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_CSV = ROOT / "data" / "cs-training.csv"
OUT_MODEL = HERE / "loans.pkl"
OUT_EXPLAINER = HERE / "loans_explainer.pkl"
META_DIR = HERE / "metadata"
OUT_MEDIANS = META_DIR / "loans_medians.json"
OUT_HINTS = META_DIR / "loans_hints.json"


# Keep this in sync with adapters/loans.py FEATURE_ORDER.
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


def _load_real() -> pd.DataFrame | None:
    if not DATA_CSV.exists():
        return None
    df = pd.read_csv(DATA_CSV)
    df = df.rename(columns={"SeriousDlqin2yrs": "y"})
    for col in ("MonthlyIncome", "NumberOfDependents"):
        df[col] = df[col].fillna(df[col].median())
    df = df[df["age"] > 0]
    return df[FEATURE_ORDER + ["y"]]


def _synth(n: int = 40_000, seed: int = 7) -> pd.DataFrame:
    """Generate a synthetic dataset with realistic-ish credit structure."""
    rng = np.random.default_rng(seed)
    age = rng.integers(21, 72, size=n)
    income = np.clip(rng.lognormal(mean=10.8, sigma=0.55, size=n), 8_000, 500_000)
    dependents = rng.integers(0, 5, size=n)
    revolving = np.clip(rng.beta(2, 3, size=n) * 1.1, 0, 1.5)
    debt_ratio = np.clip(rng.beta(2, 4, size=n) * 1.2, 0, 2.0)
    open_lines = rng.integers(0, 18, size=n)
    real_estate = rng.integers(0, 4, size=n)
    late30 = rng.choice([0, 1, 2, 3], size=n, p=[0.72, 0.18, 0.07, 0.03])
    late60 = rng.choice([0, 1, 2], size=n, p=[0.90, 0.08, 0.02])
    late90 = rng.choice([0, 1, 2], size=n, p=[0.94, 0.05, 0.01])

    # Latent risk driven by the fields we want SHAP to highlight.
    score = (
        2.2 * (debt_ratio - 0.31)
        + 1.7 * (revolving - 0.30)
        + 0.9 * late30
        + 1.6 * late60
        + 2.4 * late90
        - 0.5 * np.log1p(income / 20_000)
        + 0.2 * (open_lines / 5)
    )
    prob_bad = 1.0 / (1.0 + np.exp(-score))
    y = (rng.random(n) < prob_bad).astype(int)

    return pd.DataFrame(
        {
            "RevolvingUtilizationOfUnsecuredLines": revolving,
            "age": age,
            "NumberOfTime30-59DaysPastDueNotWorse": late30,
            "DebtRatio": debt_ratio,
            "MonthlyIncome": income,
            "NumberOfOpenCreditLinesAndLoans": open_lines,
            "NumberOfTimes90DaysLate": late90,
            "NumberRealEstateLoansOrLines": real_estate,
            "NumberOfTime60-89DaysPastDueNotWorse": late60,
            "NumberOfDependents": dependents,
            "y": y,
        }
    )


def _precompute_hints(model: XGBClassifier, df_approved: pd.DataFrame) -> dict:
    from seed_cases import SEED_CASES  # local import avoids circular load

    hints: dict[str, list[dict]] = {}
    contestable = [
        "DebtRatio",
        "MonthlyIncome",
        "RevolvingUtilizationOfUnsecuredLines",
        "NumberOfTime30-59DaysPastDueNotWorse",
    ]
    evidence_for = {
        "DebtRatio": "loan_payoff_receipt",
        "MonthlyIncome": "pay_stub",
        "RevolvingUtilizationOfUnsecuredLines": "credit_card_statement",
        "NumberOfTime30-59DaysPastDueNotWorse": "payment_history",
    }
    for case_id, case in SEED_CASES.items():
        cfs: list[dict] = []
        for feat in contestable:
            approved_median = float(df_approved[feat].median())
            current = float(case["features"].get(feat, 0))
            if abs(approved_median - current) < 1e-6:
                continue
            cfs.append(
                {
                    "feature": feat,
                    "evidence_type": evidence_for[feat],
                    "target_value_hint": round(approved_median, 4),
                    "source": "offline_cf_approx",
                }
            )
        hints[case_id] = cfs[:3]
    return hints


def main() -> None:
    META_DIR.mkdir(parents=True, exist_ok=True)

    df = _load_real()
    if df is None:
        print("[train_loans] no real dataset found; using synthetic", file=sys.stderr)
        df = _synth()
    else:
        print(f"[train_loans] loaded {len(df):,} rows from {DATA_CSV}", file=sys.stderr)

    X = df[FEATURE_ORDER]
    y = df["y"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss",
        tree_method="hist",
    )
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    print(f"[train_loans] test accuracy = {score:.3f}", file=sys.stderr)

    explainer = shap.TreeExplainer(model)

    joblib.dump(model, OUT_MODEL)
    joblib.dump(explainer, OUT_EXPLAINER)
    print(f"[train_loans] wrote {OUT_MODEL.name} + {OUT_EXPLAINER.name}", file=sys.stderr)

    # Approved-applicant medians for novel-input fallback.
    approved = df[df["y"] == 0]
    medians = {k: float(round(approved[k].median(), 4)) for k in FEATURE_ORDER}
    with OUT_MEDIANS.open("w") as f:
        json.dump(medians, f, indent=2)

    # Counterfactual hints per seed case.
    sys.path.insert(0, str(ROOT))
    hints = _precompute_hints(model, approved)
    with OUT_HINTS.open("w") as f:
        json.dump(hints, f, indent=2)

    print(f"[train_loans] wrote {OUT_MEDIANS.name} + {OUT_HINTS.name}", file=sys.stderr)
    print("[train_loans] done.", file=sys.stderr)


if __name__ == "__main__":
    main()
