"""Check 7 — Plausibility vs baseline. Wild jumps (e.g., 10× income) are flagged."""
from __future__ import annotations

from .types import CheckResult, EvidenceContext


def check(ctx: EvidenceContext) -> CheckResult:
    if ctx.claimed_value is None or ctx.prior_value is None:
        return CheckResult(
            name="plausibility_vs_baseline",
            passed=True,
            severity="low",
            detail="No prior baseline to compare against.",
        )
    prior = max(abs(ctx.prior_value), 1e-9)
    ratio = ctx.claimed_value / prior if prior else float("inf")
    limit = max(ctx.realistic_delta_multiplier, 1.5)
    if ratio == 0:
        # dropping to zero from a nonzero baseline is suspicious for monetary fields
        return CheckResult(
            name="plausibility_vs_baseline",
            passed=False,
            severity="medium",
            detail=f"Value dropped to 0 from prior {ctx.prior_value}.",
        )
    if 1 / limit <= ratio <= limit:
        return CheckResult(
            name="plausibility_vs_baseline",
            passed=True,
            severity="low",
            detail=f"{ratio:.2f}× prior ({ctx.prior_value} → {ctx.claimed_value}); within {limit:.1f}× multiplier.",
            data={"ratio": ratio},
        )
    return CheckResult(
        name="plausibility_vs_baseline",
        passed=False,
        severity="medium",
        detail=(
            f"Implausible delta: {ratio:.2f}× prior ({ctx.prior_value} → {ctx.claimed_value}). "
            f"Allowed range was {1/limit:.2f}× to {limit:.1f}×."
        ),
        data={"ratio": ratio},
    )
