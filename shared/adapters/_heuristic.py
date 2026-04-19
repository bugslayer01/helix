"""Base scaffolding for rule-based (non-ML) domain adapters.

Each heuristic adapter defines:
  - a feature spec (list of dicts with feature/weight/baseline/direction/display)
  - verbs, profile_groups, path_reasons, legal_citations
  - optional FORM_KEY_MAP

Given the spec, this module computes predict / explain / feature_schema so the
adapter file itself can stay small.
"""

from __future__ import annotations

import math
from typing import Any, Callable

from ._shared import (
    UNIVERSAL_CONTEST_REASONS,
    UNIVERSAL_REVIEW_REASONS,
    identity_sha256,
)


class HeuristicAdapter:
    """Generic adapter driven by a declarative feature spec.

    Subclasses set class attributes; this base computes predict/explain.
    """

    domain_id: str = "heuristic"
    display_name: str = "Heuristic domain"
    features: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    copy: dict[str, str] = {}
    citations: list[str] = []
    form_key_map: dict[str, str] = {}
    bias: float = 0.0
    custom_contest_reasons: list[dict[str, str]] | None = None
    custom_review_reasons: list[dict[str, str]] | None = None

    def __init__(self) -> None:
        self.model_version_hash = identity_sha256(
            f"{self.domain_id}:{len(self.features)}:{self.bias}"
        )

    # ---- prediction -----------------------------------------------------

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        features = self._normalize(features)
        score = self.bias + sum(
            self._normalized_contribution(f, features) for f in self.features
        )
        prob_bad = 1.0 / (1.0 + math.exp(-score))
        approved = prob_bad < 0.5
        return {
            "decision": "approved" if approved else "denied",
            "confidence": round(1.0 - prob_bad, 4),
            "prob_bad": round(prob_bad, 4),
        }

    def explain(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        features = self._normalize(features)
        rows: list[dict[str, Any]] = []
        for f in self.features:
            raw_contribution = self._normalized_contribution(f, features)
            # flip sign so positive = toward approval
            contribution = -raw_contribution
            value = features.get(f["feature"], 0)
            display_fn: Callable[[Any], str] = f.get("display", lambda v: str(v))
            rows.append(
                {
                    "feature": f["feature"],
                    "display_name": f["display_name"],
                    "value": value,
                    "value_display": display_fn(value),
                    "contribution": round(contribution, 4),
                    "contestable": bool(f.get("contestable", True)),
                    "protected": bool(f.get("protected", False)),
                }
            )
        return rows

    def feature_schema(self) -> list[dict[str, Any]]:
        reverse = {v: k for k, v in self.form_key_map.items()}
        return [
            {
                "feature": f["feature"],
                "form_key": reverse.get(f["feature"], f["feature"]),
                "display_name": f["display_name"],
                "group": f.get("group", "default"),
                "contestable": bool(f.get("contestable", True)),
                "protected": bool(f.get("protected", False)),
                # correction_policy drives what the user can do:
                #   "user_editable"   — user types a proposed new value + attaches evidence
                #   "evidence_driven" — user can't type; evidence upload triggers recompute
                #   "locked"          — displayed but not contestable via Path 1
                "correction_policy": f.get(
                    "correction_policy",
                    "locked"
                    if f.get("protected") or not f.get("contestable", True)
                    else "user_editable",
                ),
                "evidence_types": list(f.get("evidence_types", [])),
                "unit": f.get("unit", ""),
                "hint": f.get("hint", ""),
                "hint_placeholder": f.get("placeholder", ""),
                "min": f.get("min"),
                "max": f.get("max"),
                "step": f.get("step"),
                "realistic_delta_multiplier": float(f.get("delta_multiplier", 3.0)),
            }
            for f in self.features
        ]

    def suggest_counterfactual(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        features = self._normalize(features)
        # Pick up to 3 biggest-negative-contribution contestable features and
        # suggest their "approval baseline" as the target.
        rows = sorted(
            (f for f in self.features if f.get("contestable") and not f.get("protected")),
            key=lambda f: abs(self._normalized_contribution(f, features)),
            reverse=True,
        )
        hints: list[dict[str, Any]] = []
        for f in rows[:3]:
            ev = f.get("evidence_types", ["supporting_document"])
            if self._normalized_contribution(f, features) <= 0.01:
                continue
            hints.append(
                {
                    "feature": f["feature"],
                    "evidence_type": ev[0] if ev else "supporting_document",
                    "target_value_hint": f.get("approval_baseline", f.get("baseline", 0)),
                    "source": "heuristic_baseline",
                }
            )
        return hints

    def verbs(self) -> dict[str, str]:
        return dict(self.copy)

    def profile_groups(self) -> list[dict[str, Any]]:
        return [dict(g) for g in self.groups]

    def path_reasons(self) -> dict[str, list[dict[str, str]]]:
        return {
            "contest": [dict(r) for r in (self.custom_contest_reasons or UNIVERSAL_CONTEST_REASONS)],
            "review": [dict(r) for r in (self.custom_review_reasons or UNIVERSAL_REVIEW_REASONS)],
        }

    def legal_citations(self) -> list[str]:
        return list(self.citations)

    # ---- evidence seams (default stubs; domain adapters can override) ----

    def intake_doc_types(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "supporting_document",
                "display_name": "Supporting document",
                "accepted_mime": ["application/pdf", "image/png", "image/jpeg"],
                "required": False,
                "freshness_days": 365,
            }
        ]

    def evidence_doc_types(self, target_feature: str) -> list[dict[str, Any]]:
        return self.intake_doc_types()

    def extract_prompt(self, doc_type: str) -> dict[str, Any]:
        return {
            "prompt": f"Extract key fields from this {doc_type.replace('_', ' ')}.",
            "schema": {
                "type": "object",
                "properties": {
                    "doc_type": {"type": "string"},
                    "issuer": {"type": "string"},
                    "issue_date": {"type": "string"},
                },
                "required": ["doc_type"],
            },
            "feature_field": None,
        }

    # ---- internals ------------------------------------------------------

    def _normalize(self, features: dict[str, Any]) -> dict[str, Any]:
        out = dict(features)
        for form_key, model_key in self.form_key_map.items():
            if form_key in features and form_key != model_key:
                try:
                    out[model_key] = float(features[form_key])
                except (TypeError, ValueError):
                    out[model_key] = features[form_key]
        return out

    def _normalized_contribution(self, f: dict[str, Any], features: dict[str, Any]) -> float:
        """Return weight × (value - baseline) / scale, toward the BAD class."""
        value = features.get(f["feature"], f.get("baseline", 0))
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0.0
        baseline = float(f.get("baseline", 0.0))
        scale = float(f.get("scale", 1.0) or 1.0)
        weight = float(f.get("weight", 0.0))
        direction = float(f.get("direction", 1.0))  # +1: higher = worse; -1: higher = better
        return direction * weight * (value - baseline) / scale
