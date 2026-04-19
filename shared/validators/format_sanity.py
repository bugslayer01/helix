"""Check 6 — Basic format hygiene: currency symbols, parseable dates, masked accounts."""
from __future__ import annotations

import re

from .types import CheckResult, EvidenceContext

_CURRENCY = re.compile(r"(?:₹|INR|Rs\.?|USD|\$|EUR|€|GBP|£)", re.IGNORECASE)
_DATE = re.compile(r"\b\d{1,4}[-/]\d{1,2}[-/]\d{1,4}\b")
_BARE_ACCOUNT = re.compile(r"\b\d{10,18}\b")
_MASKED_ACCOUNT = re.compile(r"(?:\*|x){2,}\d{2,6}\b", re.IGNORECASE)


def check(ctx: EvidenceContext) -> CheckResult:
    text = ctx.extraction_text_layer or ""
    fields = ctx.extraction_fields or {}
    notes: list[str] = []
    severity: str = "low"
    passed = True

    # Currency symbol expected on money-bearing docs.
    monetary_doc_types = {"payslip", "bank_statement", "card_statement", "loan_payoff_letter"}
    if (fields.get("doc_type") or ctx.doc_type_expected) in monetary_doc_types:
        if not _CURRENCY.search(text):
            notes.append("no_currency_symbol")
            severity = "low"
            # still 'passed' but flagged low

    # Dates must parse somewhere.
    if not _DATE.search(text):
        notes.append("no_parseable_date")
        severity = "medium"
        passed = False

    # Account number should be masked if present.
    if _BARE_ACCOUNT.search(text) and not _MASKED_ACCOUNT.search(text):
        notes.append("unmasked_account_number")
        severity = "medium"

    detail = "Format hygiene OK." if passed and not notes else "; ".join(notes)
    return CheckResult(
        name="format_sanity",
        passed=passed,
        severity=severity if not passed else "low",
        detail=detail,
    )
