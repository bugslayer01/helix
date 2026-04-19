"""Simulated async evidence validator.

Runs as a background task spawned from the propose handler. Each proposal
"validates" in 1-3 seconds. Outcomes are deterministic per (contest_id, feature)
so the same contest always reaches the same terminal state.
"""

from __future__ import annotations

import asyncio
import hashlib
import random
from typing import Any

from shared.adapters import get_adapter
from seed_cases import DEMO_SAFE_CASE_IDS, SEED_CASES
from services import audit_log, evidence_store


REJECTION_REASONS = [
    "Evidence document hash not recognised by the credit bureau",
    "Proposed value exceeds realistic bounds for this evidence type",
    "Evidence filename does not match the declared document type",
    "Bureau record on file is more recent than the supplied evidence",
]


def _seed_for(contest_id: str, feature: str) -> int:
    h = hashlib.sha256(f"{contest_id}|{feature}".encode()).digest()
    return int.from_bytes(h[:8], "big")


def simulate_validation_result(
    case_id: str,
    contest_id: str,
    feature: str,
) -> dict[str, Any]:
    """Deterministic pass/fail decision. Demo-safe cases always pass."""
    if case_id in DEMO_SAFE_CASE_IDS:
        return {"passed": True, "note": None}
    rng = random.Random(_seed_for(contest_id, feature))
    if rng.random() < 0.85:
        return {"passed": True, "note": None}
    return {"passed": False, "note": rng.choice(REJECTION_REASONS)}


def _resolved_value_for(
    adapter: Any,
    feature: str,
    policy: str,
    proposed_value: float | None,
    case_id: str | None = None,
    case_features: dict[str, Any] | None = None,
) -> float | None:
    if policy == "user_editable":
        return proposed_value
    # evidence_driven: find the approval_baseline / counterfactual hint.
    schema_rows = adapter.feature_schema()
    schema_by_feature = {r["feature"]: r for r in schema_rows}
    row = schema_by_feature.get(feature, {})

    # Ask the adapter for counterfactual hints. Pass the case's known features
    # (plus _case_id) so the loans adapter can look up its precomputed hint.
    probe = {**(case_features or {})}
    if case_id:
        probe["_case_id"] = case_id
    try:
        hints = adapter.suggest_counterfactual(probe)
    except Exception:
        hints = []
    for h in hints or []:
        if h.get("feature") == feature and h.get("target_value_hint") is not None:
            try:
                return float(h["target_value_hint"])
            except (TypeError, ValueError):
                pass
    # Heuristic-spec baseline as the fallback.
    if hasattr(adapter, "features"):
        for f in adapter.features:  # type: ignore[attr-defined]
            if f.get("feature") == feature:
                return float(
                    f.get("approval_baseline", f.get("baseline", 0)) or 0
                )
    return row.get("min") or 0.0


async def _validate_one(
    contest_id: str,
    case_id: str,
    adapter: Any,
    proposal: dict[str, Any],
) -> None:
    rng = random.Random(_seed_for(contest_id, proposal["feature"]))
    delay = 1.0 + rng.random() * 2.0  # 1.0 – 3.0s
    await asyncio.sleep(delay)

    outcome = simulate_validation_result(case_id, contest_id, proposal["feature"])
    if outcome["passed"]:
        case = SEED_CASES.get(case_id) or {}
        resolved = _resolved_value_for(
            adapter,
            proposal["feature"],
            proposal["policy"],
            proposal.get("proposed_value"),
            case_id=case_id,
            case_features=case.get("features"),
        )
        evidence_store.update_proposal(
            proposal["id"],
            status="validated",
            resolved_value=float(resolved) if resolved is not None else None,
            validation_note=None,
        )
        audit_log.append(
            case_id=case_id,
            action="evidence_validated",
            title="Evidence validated",
            subtitle=f"{proposal['feature']} · accepted",
            payload={
                "contest_id": contest_id,
                "proposal_id": proposal["id"],
                "feature": proposal["feature"],
                "resolved_value": resolved,
            },
            kind="success",
        )
    else:
        evidence_store.update_proposal(
            proposal["id"],
            status="rejected",
            resolved_value=None,
            validation_note=outcome["note"],
        )
        audit_log.append(
            case_id=case_id,
            action="evidence_rejected",
            title="Evidence rejected",
            subtitle=f"{proposal['feature']} · {outcome['note']}",
            payload={
                "contest_id": contest_id,
                "proposal_id": proposal["id"],
                "feature": proposal["feature"],
                "note": outcome["note"],
            },
            kind="warning",
        )


async def run_validation(contest_id: str) -> None:
    contest = evidence_store.get_contest(contest_id)
    if contest is None:
        return
    case_id = contest["case_id"]
    case = SEED_CASES.get(case_id)
    if case is None:
        return
    adapter = get_adapter(case["domain"])
    await asyncio.gather(
        *(
            _validate_one(contest_id, case_id, adapter, p)
            for p in contest["proposals"]
        )
    )
    # After every proposal has resolved, flip the contest's aggregate status.
    latest = evidence_store.get_contest(contest_id)
    if latest is None:
        return
    agg = evidence_store.compute_aggregate_status(latest["proposals"])
    evidence_store.set_contest_status(contest_id, agg)
