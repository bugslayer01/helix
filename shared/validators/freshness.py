"""Check 2 — Document is recent enough to reflect current reality."""
from __future__ import annotations

from datetime import date, datetime

from .types import CheckResult, EvidenceContext

# Per-doc-type freshness windows (days).
FRESHNESS_DAYS = {
    "payslip": (90, 180),
    "bank_statement": (120, 240),
    "credit_report": (30, 90),
    "income_tax_return": (550, 730),
    "card_statement": (60, 120),
}


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def check(ctx: EvidenceContext) -> CheckResult:
    fields = ctx.extraction_fields or {}
    issue_date = _parse_date(
        fields.get("issue_date")
        or fields.get("pay_period_end")
        or fields.get("report_date")
        or fields.get("statement_period_end")
    )
    doc_type = fields.get("doc_type") or ctx.doc_type_expected
    strict_days, lenient_days = FRESHNESS_DAYS.get(doc_type, (90, 180))

    if issue_date is None:
        return CheckResult(
            name="freshness",
            passed=False,
            severity="medium",
            detail="No issue date detected on the document. Cannot confirm freshness.",
        )
    age_days = (date.today() - issue_date).days
    if age_days < 0:
        return CheckResult(
            name="freshness",
            passed=False,
            severity="high",
            detail=f"Document issue date is in the future: {issue_date.isoformat()}.",
        )
    if age_days <= strict_days:
        return CheckResult(
            name="freshness",
            passed=True,
            severity="low",
            detail=f"Issued {issue_date.isoformat()} ({age_days} days old).",
            data={"age_days": age_days},
        )
    if age_days <= lenient_days:
        return CheckResult(
            name="freshness",
            passed=True,
            severity="low",
            detail=f"Issued {issue_date.isoformat()} ({age_days} days old) — within lenient window.",
            data={"age_days": age_days},
        )
    return CheckResult(
        name="freshness",
        passed=False,
        severity="high",
        detail=f"Document is {age_days} days old; exceeds lenient window of {lenient_days} days.",
        data={"age_days": age_days},
    )
