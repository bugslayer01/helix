"""Check 4 — Multiple docs for the same feature must agree."""
from __future__ import annotations

from .types import CheckResult, EvidenceContext

_MAX_RELATIVE_DIFF = 0.05  # 5%


def check(ctx: EvidenceContext) -> CheckResult:
    if ctx.claimed_value is None or not ctx.prior_evidence_for_feature:
        return CheckResult(
            name="cross_doc_consistency",
            passed=True,
            severity="low",
            detail="No conflicting evidence for this feature.",
        )
    conflicts = []
    for prior in ctx.prior_evidence_for_feature:
        prior_value = prior.get("extracted_value")
        if prior_value is None or prior_value == 0:
            continue
        rel = abs(ctx.claimed_value - prior_value) / max(abs(prior_value), 1e-9)
        if rel > _MAX_RELATIVE_DIFF:
            conflicts.append({"evidence_id": prior.get("id"), "value": prior_value, "rel_diff": round(rel, 3)})
    if not conflicts:
        return CheckResult(
            name="cross_doc_consistency",
            passed=True,
            severity="low",
            detail=f"Agrees with {len(ctx.prior_evidence_for_feature)} prior document(s) within 5%.",
        )
    return CheckResult(
        name="cross_doc_consistency",
        passed=False,
        severity="high",
        detail=f"Conflicts with {len(conflicts)} prior document(s).",
        data={"conflicts": conflicts},
    )
