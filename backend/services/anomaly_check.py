"""Realistic-delta bounds with a demo-safe case-id bypass."""

from __future__ import annotations

from typing import Any

from seed_cases import DEMO_SAFE_CASE_IDS


def check_anomalies(
    case_id: str,
    original_features: dict[str, Any],
    updates: dict[str, Any],
    feature_schema: list[dict[str, Any]],
) -> list[str]:
    """Return a list of anomaly flag strings; empty means clean."""
    if case_id in DEMO_SAFE_CASE_IDS:
        return []

    schema_by_key = {s["feature"]: s for s in feature_schema}
    flags: list[str] = []
    for key, new_raw in updates.items():
        schema = schema_by_key.get(key)
        if schema is None:
            continue
        try:
            new_val = float(new_raw)
            old_val = float(original_features.get(key, 0) or 0)
        except (TypeError, ValueError):
            continue
        if old_val == 0:
            continue
        multiplier = schema.get("realistic_delta_multiplier", 3.0)
        if new_val > old_val * multiplier or new_val < old_val / multiplier:
            flags.append(
                f"{key}_delta_exceeds_{multiplier}x"
            )
    return flags
