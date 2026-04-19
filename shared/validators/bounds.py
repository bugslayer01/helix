"""Check 3 — Extracted value falls inside the feature's sane bounds."""
from __future__ import annotations

from .types import CheckResult, EvidenceContext


def check(ctx: EvidenceContext) -> CheckResult:
    if ctx.claimed_value is None:
        return CheckResult(
            name="bounds",
            passed=False,
            severity="medium",
            detail="No numeric value extracted; nothing to bound-check.",
        )
    lo, hi = ctx.feature_bounds
    if lo is not None and ctx.claimed_value < lo:
        return CheckResult(
            name="bounds",
            passed=False,
            severity="high",
            detail=f"Value {ctx.claimed_value} below minimum {lo}.",
        )
    if hi is not None and ctx.claimed_value > hi:
        return CheckResult(
            name="bounds",
            passed=False,
            severity="high",
            detail=f"Value {ctx.claimed_value} above maximum {hi}.",
        )
    return CheckResult(
        name="bounds",
        passed=True,
        severity="low",
        detail=f"Value {ctx.claimed_value} within [{lo}, {hi}].",
    )
