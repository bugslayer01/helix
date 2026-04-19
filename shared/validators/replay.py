"""Check 10 — Replay detection via SHA-256 hash index."""
from __future__ import annotations

from .types import CheckResult, EvidenceContext


def check(ctx: EvidenceContext) -> CheckResult:
    hit = ctx.replay_index_hit
    if not hit:
        return CheckResult(
            name="replay",
            passed=True,
            severity="low",
            detail=f"SHA-256 {ctx.upload_sha256[:16]}… not seen before.",
        )
    first_case = hit.get("first_case_id")
    seen_count = hit.get("seen_count", 1)
    if first_case == ctx.case_id and seen_count == 1:
        return CheckResult(
            name="replay",
            passed=True,
            severity="low",
            detail="Previously uploaded and then removed within this same case.",
        )
    return CheckResult(
        name="replay",
        passed=False,
        severity="high",
        detail=(
            f"Document SHA-256 already on file (first seen in case {first_case}, "
            f"seen {seen_count} times total)."
        ),
        data=hit,
    )
