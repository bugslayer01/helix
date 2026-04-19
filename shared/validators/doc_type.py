"""Check 1 — Document type matches the feature being contested."""
from __future__ import annotations

from .types import CheckResult, EvidenceContext

# Maps feature → acceptable document types.
FEATURE_DOC_TYPES = {
    "MonthlyIncome": {"payslip", "bank_statement", "income_tax_return"},
    "DebtRatio": {"bank_statement", "credit_report", "loan_payoff_letter"},
    "RevolvingUtilizationOfUnsecuredLines": {"credit_report", "card_statement"},
    "NumberOfOpenCreditLinesAndLoans": {"credit_report"},
    "NumberRealEstateLoansOrLines": {"credit_report", "loan_payoff_letter"},
    "NumberOfTime30-59DaysPastDueNotWorse": {"credit_report"},
    "NumberOfTime60-89DaysPastDueNotWorse": {"credit_report"},
    "NumberOfTimes90DaysLate": {"credit_report"},
    "NumberOfDependents": {"id_document", "government_form"},
}


def check(ctx: EvidenceContext) -> CheckResult:
    detected = (ctx.extraction_fields or {}).get("doc_type") or ctx.doc_type_expected
    allowed = FEATURE_DOC_TYPES.get(ctx.target_feature, {ctx.doc_type_expected})
    if detected in allowed:
        return CheckResult(
            name="doc_type_matches_claim",
            passed=True,
            severity="low",
            detail=f"Classified as {detected!r}; acceptable for target feature {ctx.target_feature}.",
        )
    return CheckResult(
        name="doc_type_matches_claim",
        passed=False,
        severity="high",
        detail=(
            f"Uploaded document classified as {detected!r}, which does not support "
            f"a correction for {ctx.target_feature}."
        ),
    )
