"""Train an XGBoost credit-risk classifier.

Prefers real ``data/cs-training.csv`` (the public Give Me Some Credit dataset)
when present; falls back to a stronger synthetic generator with sharper
class separation tuned to make SHAP signs intuitive.

Outputs:
  models/loans.pkl                — trained XGBoost (calibrated via Platt)
  models/loans_explainer.pkl      — fitted shap.TreeExplainer (raw booster)
  models/metadata/loans_medians.json — population medians (per feature)
  models/metadata/loans_hints.json   — counterfactual hints per case (read from
                                       scripts/seed/loans/cases/case*.json)

Run:
    backend/.venv/bin/python -m shared.models.train_loans
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parent
DATA_CSV = REPO / "data" / "cs-training.csv"
OUT_MODEL = HERE / "loans.pkl"
OUT_EXPLAINER = HERE / "loans_explainer.pkl"
META_DIR = HERE / "metadata"
OUT_MEDIANS = META_DIR / "loans_medians.json"
OUT_HINTS = META_DIR / "loans_hints.json"
CASES_DIR = REPO / "scripts" / "seed" / "loans" / "cases"


# Keep this in sync with shared/adapters/loans.py FEATURE_ORDER.
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


def _synth(n: int = 60_000, seed: int = 7) -> pd.DataFrame:
    """Stronger synthetic dataset.

    Compared to the previous version: clearer linear signal on the three demo
    features (revolving utilization, debt ratio, monthly income), heavier
    coefficients, less noise. This keeps SHAP signs intuitive on common
    feature vectors instead of being dominated by interaction effects.
    """
    rng = np.random.default_rng(seed)
    age = rng.integers(21, 72, size=n)
    income = np.clip(rng.lognormal(mean=10.7, sigma=0.45, size=n), 8_000, 500_000)
    dependents = rng.integers(0, 5, size=n)
    revolving = np.clip(rng.beta(2.5, 3, size=n) * 1.05, 0, 1.5)
    debt_ratio = np.clip(rng.beta(2.5, 4, size=n) * 1.1, 0, 2.0)
    open_lines = rng.integers(0, 18, size=n)
    real_estate = rng.integers(0, 4, size=n)
    late30 = rng.choice([0, 1, 2, 3], size=n, p=[0.74, 0.17, 0.06, 0.03])
    late60 = rng.choice([0, 1, 2], size=n, p=[0.91, 0.07, 0.02])
    late90 = rng.choice([0, 1, 2], size=n, p=[0.95, 0.04, 0.01])

    # Latent risk: stronger weights on the three contestable features so SHAP
    # tells a clean story for those. Income enters log-transformed.
    score = (
        3.5 * (revolving - 0.30)
        + 3.2 * (debt_ratio - 0.31)
        - 1.4 * np.log1p(income / 25_000)
        + 1.1 * late30
        + 2.0 * late60
        + 3.0 * late90
        + 0.18 * (open_lines / 5)
        + 0.04 * dependents
    )
    # Add a small noise term so the model isn't perfectly separable.
    score += rng.normal(scale=0.55, size=n)
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


def _load_seed_cases() -> dict[str, dict]:
    """Read every case.json under scripts/seed/loans/cases/ for hint precompute."""
    out: dict[str, dict] = {}
    if not CASES_DIR.exists():
        return out
    for d in sorted(CASES_DIR.iterdir()):
        case_json = d / "case.json"
        if case_json.exists():
            try:
                spec = json.loads(case_json.read_text())
                if "intake_features" in spec and "application_id" in spec:
                    out[spec["application_id"]] = spec
            except Exception:
                continue
    return out


def _precompute_hints(df_approved: pd.DataFrame) -> dict[str, list[dict]]:
    cases = _load_seed_cases()
    if not cases:
        return {}
    contestable = [
        "DebtRatio",
        "MonthlyIncome",
        "RevolvingUtilizationOfUnsecuredLines",
        "NumberOfTime30-59DaysPastDueNotWorse",
    ]
    evidence_for = {
        "DebtRatio": "loan_payoff_letter",
        "MonthlyIncome": "payslip",
        "RevolvingUtilizationOfUnsecuredLines": "credit_report",
        "NumberOfTime30-59DaysPastDueNotWorse": "credit_report",
    }
    hints: dict[str, list[dict]] = {}
    for case_id, spec in cases.items():
        cfs: list[dict] = []
        for feat in contestable:
            approved_median = float(df_approved[feat].median())
            current = float(spec["intake_features"].get(feat, 0))
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
    base = XGBClassifier(
        n_estimators=180,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=4,
        reg_lambda=1.0,
        random_state=42,
        eval_metric="logloss",
        tree_method="hist",
    )
    base.fit(X_train, y_train)
    raw_probs = base.predict_proba(X_test)[:, 1]
    raw_auc = roc_auc_score(y_test, raw_probs)

    # Wrap in Platt scaling so prob_bad is properly calibrated.
    calibrated = CalibratedClassifierCV(base, cv="prefit", method="sigmoid")
    calibrated.fit(X_train, y_train)
    cal_probs = calibrated.predict_proba(X_test)[:, 1]
    cal_auc = roc_auc_score(y_test, cal_probs)
    cal_acc = (cal_probs >= 0.5).astype(int).eq(y_test.reset_index(drop=True)).mean() if hasattr(cal_probs, 'eq') else float(((cal_probs >= 0.5).astype(int) == y_test.values).mean())
    print(f"[train_loans] raw AUROC={raw_auc:.3f}  calibrated AUROC={cal_auc:.3f}  acc@0.5={cal_acc:.3f}", file=sys.stderr)

    explainer = shap.TreeExplainer(base)

    joblib.dump(calibrated, OUT_MODEL)
    joblib.dump(explainer, OUT_EXPLAINER)
    print(f"[train_loans] wrote {OUT_MODEL.name} + {OUT_EXPLAINER.name}", file=sys.stderr)

    approved = df[df["y"] == 0]
    medians = {k: float(round(approved[k].median(), 4)) for k in FEATURE_ORDER}
    with OUT_MEDIANS.open("w") as f:
        json.dump(medians, f, indent=2)

    hints = _precompute_hints(approved)
    with OUT_HINTS.open("w") as f:
        json.dump(hints, f, indent=2)

    print(f"[train_loans] wrote {OUT_MEDIANS.name} + {OUT_HINTS.name}", file=sys.stderr)
    print("[train_loans] done.", file=sys.stderr)


if __name__ == "__main__":
    main()
