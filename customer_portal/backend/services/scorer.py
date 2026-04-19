"""LenderCo scoring wrapper. Uses shared.adapters.loans to produce the decision."""
from __future__ import annotations

from typing import Any

from shared.adapters import get_adapter


def score(domain: str, features: dict[str, Any]) -> dict[str, Any]:
    adapter = get_adapter(domain)
    prediction = adapter.predict(features)
    shap = adapter.explain(features)
    top_reasons = _top_reasons(shap, prediction["decision"])
    return {
        "verdict": prediction["decision"],
        "prob_bad": prediction["prob_bad"],
        "confidence": prediction["confidence"],
        "shap": shap,
        "top_reasons": top_reasons,
        "model_version": adapter.model_version_hash,
    }


def _top_reasons(shap: list[dict[str, Any]], verdict: str, k: int = 3) -> list[str]:
    if not shap:
        return []
    # Sort by the direction that drove the outcome.
    sign = -1 if verdict == "denied" else 1
    ranked = sorted(
        (r for r in shap if not r.get("protected")),
        key=lambda r: sign * r.get("contribution", 0),
    )
    reasons: list[str] = []
    for row in ranked[:k]:
        display_name = row.get("display_name") or row.get("feature")
        value_display = row.get("value_display") or row.get("value")
        reasons.append(f"{display_name}: {value_display}")
    return reasons
