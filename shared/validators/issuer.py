"""Check 5 — Issuer / letterhead / attribution is present."""
from __future__ import annotations

import re

from .types import CheckResult, EvidenceContext

_ATTRIBUTION_HINTS = re.compile(
    r"(?:employer|issued\s*by|bank\s*name|cin|pan|gstin|uid|aadhaar|experian|equifax|cibil|transunion|crif)",
    re.IGNORECASE,
)


def check(ctx: EvidenceContext) -> CheckResult:
    fields = ctx.extraction_fields or {}
    issuer_field = fields.get("issuer") or fields.get("employer") or fields.get("bank") or fields.get("bureau")
    text_hit = bool(_ATTRIBUTION_HINTS.search(ctx.extraction_text_layer or ""))
    if issuer_field:
        return CheckResult(
            name="issuer_present",
            passed=True,
            severity="low",
            detail=f"Issuer: {issuer_field}.",
            data={"issuer": issuer_field},
        )
    if text_hit:
        return CheckResult(
            name="issuer_present",
            passed=True,
            severity="low",
            detail="Attribution markers found in document text.",
        )
    return CheckResult(
        name="issuer_present",
        passed=False,
        severity="medium",
        detail="No issuer, letterhead, or attribution marker detected.",
    )
