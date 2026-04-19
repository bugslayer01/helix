"""Generate every case fixture from a single in-memory spec.

Run from repo root:

    backend/.venv/bin/python -m scripts.seed.loans.cases.build_all

Produces ``case<N>/intake/`` (intake docs), ``case<N>/evidence/`` (clean
contest evidence) and ``case<N>/adversarial/`` (Shield-failure samples) for
every case below. Also writes ``case<N>/case.json`` with the applicant
record, intake feature overrides, and any per-case metadata used by
``scripts/seed.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import _lib

HERE = Path(__file__).resolve().parent

# -----------------------------------------------------------------------------
# Case specs
# -----------------------------------------------------------------------------

CASES = {
    "case1": {
        "name": "Priya Sharma",
        "applicant_id": "APP-A4F2-9E31",
        "application_id": "LN-2026-A4F2",
        "dob": "1990-03-12",
        "email": "priya.sharma@example.com",
        "phone": "+91 98100 54321",
        "amount": 500000,
        "purpose": "Home renovation",
        "employer": "Infosys Limited",
        "bank": "HDFC Bank",
        "bureau": "Experian",
        "intake": {
            "payslip": {"period_month": "2026-03", "issue_date": "2026-03-31", "gross": 62000, "net": 48000},
            "bank_statement": {"avg_balance": 12400, "closing": 14900},
            "credit_report": {"utilization_pct": 68, "score": 702, "open_lines": 4},
        },
        # explicit feature overrides written into scored_features so the demo
        # case lands in a known state regardless of extractor noise
        "intake_features": {
            "RevolvingUtilizationOfUnsecuredLines": 0.68,
            "DebtRatio": 0.42,
            "MonthlyIncome": 48000.0,
            "NumberOfOpenCreditLinesAndLoans": 4.0,
            "NumberOfTimes90DaysLate": 0.0,
            "NumberRealEstateLoansOrLines": 1.0,
            "NumberOfTime30-59DaysPastDueNotWorse": 0.0,
            "NumberOfTime60-89DaysPastDueNotWorse": 0.0,
            "NumberOfDependents": 2.0,
        },
        "evidence": {
            "payslip_promotion": {"period_month": "2026-04", "issue_date": "2026-04-19", "gross": 82000, "net": 68000},
            "credit_report_repaired": {"utilization_pct": 38, "score": 741},
            "bank_statement_healthy": {"avg_balance": 95000, "closing": 102000},
        },
        "story": "Income up after promotion, paid down credit cards. Designed to flip.",
    },
    "case2": {
        "name": "Rohan Mehta",
        "applicant_id": "APP-7F11-A001",
        "application_id": "LN-2026-7F11",
        "dob": "1986-11-04",
        "email": "rohan.mehta@example.com",
        "phone": "+91 98201 11221",
        "amount": 800000,
        "purpose": "Debt consolidation",
        "employer": "TCS Limited",
        "bank": "ICICI Bank",
        "bureau": "CIBIL",
        "intake": {
            "payslip": {"period_month": "2026-03", "issue_date": "2026-03-31", "gross": 38000, "net": 28000},
            "bank_statement": {"avg_balance": 4800, "closing": 3200},
            "credit_report": {"utilization_pct": 92, "score": 612, "open_lines": 6, "late_30": 2, "late_60": 1, "late_90": 0},
        },
        "intake_features": {
            "RevolvingUtilizationOfUnsecuredLines": 0.92,
            "DebtRatio": 0.71,
            "MonthlyIncome": 28000.0,
            "NumberOfOpenCreditLinesAndLoans": 6.0,
            "NumberOfTimes90DaysLate": 0.0,
            "NumberRealEstateLoansOrLines": 0.0,
            "NumberOfTime30-59DaysPastDueNotWorse": 2.0,
            "NumberOfTime60-89DaysPastDueNotWorse": 1.0,
            "NumberOfDependents": 3.0,
        },
        "evidence": {
            "payslip_modest_raise": {"period_month": "2026-04", "issue_date": "2026-04-19", "gross": 48000, "net": 36000},
            "credit_report_modest_repair": {"utilization_pct": 78, "score": 648, "late_30": 1, "late_60": 0, "late_90": 0},
        },
        "story": "Tougher case: modest evidence improvements but still high risk. Demos a 'held' outcome.",
    },
    "case3": {
        "name": "Aditi Iyer",
        "applicant_id": "APP-9C42-B7E2",
        "application_id": "LN-2026-9C42",
        "dob": "1992-07-18",
        "email": "aditi.iyer@example.com",
        "phone": "+91 80100 22334",
        "amount": 400000,
        "purpose": "Education",
        "employer": "Wipro Limited",
        "bank": "Axis Bank",
        "bureau": "Experian",
        "intake": {
            "payslip": {"period_month": "2026-03", "issue_date": "2026-03-31", "gross": 42000, "net": 32000},
            "bank_statement": {"avg_balance": 18000, "closing": 19500},
            "credit_report": {"utilization_pct": 75, "score": 688, "open_lines": 3},
        },
        "intake_features": {
            "RevolvingUtilizationOfUnsecuredLines": 0.75,
            "DebtRatio": 0.39,
            "MonthlyIncome": 32000.0,
            "NumberOfOpenCreditLinesAndLoans": 3.0,
            "NumberOfTimes90DaysLate": 0.0,
            "NumberRealEstateLoansOrLines": 0.0,
            "NumberOfTime30-59DaysPastDueNotWorse": 0.0,
            "NumberOfTime60-89DaysPastDueNotWorse": 0.0,
            "NumberOfDependents": 1.0,
        },
        "evidence": {
            "payslip_promotion": {"period_month": "2026-04", "issue_date": "2026-04-19", "gross": 92000, "net": 72000},
            "bank_statement_inheritance": {"avg_balance": 125000, "closing": 132000},
            "credit_report_perfect": {"utilization_pct": 22, "score": 778},
        },
        "story": "Big jump in income (promotion + inheritance) plus paid-down cards. Designed to flip.",
    },
    "case4": {
        "name": "Vikram Singh",
        "applicant_id": "APP-E2A0-1234",
        "application_id": "LN-2026-E2A0",
        "dob": "1984-02-09",
        "email": "vikram.singh@example.com",
        "phone": "+91 99700 88110",
        "amount": 300000,
        "purpose": "Wedding",
        "employer": "Reliance Industries",
        "bank": "SBI",
        "bureau": "CIBIL",
        "intake": {
            "payslip": {"period_month": "2026-03", "issue_date": "2026-03-31", "gross": 145000, "net": 110000},
            "bank_statement": {"avg_balance": 480000, "closing": 510000},
            "credit_report": {"utilization_pct": 15, "score": 812, "open_lines": 3},
        },
        "intake_features": {
            "RevolvingUtilizationOfUnsecuredLines": 0.15,
            "DebtRatio": 0.18,
            "MonthlyIncome": 110000.0,
            "NumberOfOpenCreditLinesAndLoans": 3.0,
            "NumberOfTimes90DaysLate": 0.0,
            "NumberRealEstateLoansOrLines": 1.0,
            "NumberOfTime30-59DaysPastDueNotWorse": 0.0,
            "NumberOfTime60-89DaysPastDueNotWorse": 0.0,
            "NumberOfDependents": 1.0,
        },
        "evidence": {},
        "story": "Approved at intake. Useful to demo the LenderCo flow without contesting.",
    },
    "case5": {
        "name": "Sneha Patel",
        "applicant_id": "APP-3D87-CC02",
        "application_id": "LN-2026-3D87",
        "dob": "1995-09-23",
        "email": "sneha.patel@example.com",
        "phone": "+91 70203 99882",
        "amount": 600000,
        "purpose": "Medical",
        "employer": "HCL Technologies",
        "bank": "Kotak Mahindra Bank",
        "bureau": "Equifax",
        "intake": {
            "payslip": {"period_month": "2026-03", "issue_date": "2026-03-31", "gross": 52000, "net": 40000},
            "bank_statement": {"avg_balance": 9800, "closing": 8400},
            "credit_report": {"utilization_pct": 82, "score": 660, "open_lines": 5},
        },
        "intake_features": {
            "RevolvingUtilizationOfUnsecuredLines": 0.82,
            "DebtRatio": 0.55,
            "MonthlyIncome": 40000.0,
            "NumberOfOpenCreditLinesAndLoans": 5.0,
            "NumberOfTimes90DaysLate": 0.0,
            "NumberRealEstateLoansOrLines": 0.0,
            "NumberOfTime30-59DaysPastDueNotWorse": 0.0,
            "NumberOfTime60-89DaysPastDueNotWorse": 0.0,
            "NumberOfDependents": 5.0,
        },
        "evidence": {
            "payslip_promotion": {"period_month": "2026-04", "issue_date": "2026-04-19", "gross": 78000, "net": 64000},
            "credit_report_repaired": {"utilization_pct": 35, "score": 728},
        },
        "story": "Real evidence flips, but the adversarial folder demos the Shield catching forgeries.",
    },
}

# -----------------------------------------------------------------------------
# Builder
# -----------------------------------------------------------------------------


def build_case(name: str, spec: dict) -> None:
    case_dir = HERE / name
    intake_dir = case_dir / "intake"
    evidence_dir = case_dir / "evidence"
    adversarial_dir = case_dir / "adversarial"
    intake_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    adversarial_dir.mkdir(parents=True, exist_ok=True)

    # Intake docs
    intake = spec["intake"]
    payslip_intake = intake.get("payslip", {})
    if payslip_intake:
        _lib.payslip(
            intake_dir / "payslip.pdf",
            employee=spec["name"],
            employer=spec["employer"],
            pan="AXXPS1234K",
            period_month=payslip_intake["period_month"],
            issue_date=payslip_intake["issue_date"],
            gross=payslip_intake["gross"],
            net=payslip_intake["net"],
        )
    bs = intake.get("bank_statement", {})
    if bs:
        _lib.bank_statement(
            intake_dir / "bank_statement.pdf",
            holder=spec["name"],
            bank=spec["bank"],
            issue_date=payslip_intake.get("issue_date", "2026-04-01"),
            avg_balance=bs["avg_balance"],
            closing=bs["closing"],
            period_start="2026-01-01",
            period_end="2026-03-31",
        )
    cr = intake.get("credit_report", {})
    if cr:
        _lib.credit_report(
            intake_dir / "credit_report.pdf",
            holder=spec["name"],
            bureau=spec["bureau"],
            issue_date="2026-04-01",
            utilization_pct=cr.get("utilization_pct", 50),
            score=cr.get("score", 700),
            open_lines=cr.get("open_lines", 3),
            late_30=cr.get("late_30", 0),
            late_60=cr.get("late_60", 0),
            late_90=cr.get("late_90", 0),
            real_estate=cr.get("real_estate", 1),
        )

    # Clean evidence
    for ev_id, ev in spec.get("evidence", {}).items():
        if "payslip" in ev_id:
            _lib.payslip(
                evidence_dir / f"{ev_id}.pdf",
                employee=spec["name"],
                employer=spec["employer"],
                pan="AXXPS1234K",
                period_month=ev["period_month"],
                issue_date=ev["issue_date"],
                gross=ev["gross"],
                net=ev["net"],
            )
        elif "credit_report" in ev_id:
            _lib.credit_report(
                evidence_dir / f"{ev_id}.pdf",
                holder=spec["name"],
                bureau=spec["bureau"],
                issue_date=ev.get("issue_date", "2026-04-19"),
                utilization_pct=ev["utilization_pct"],
                score=ev["score"],
                open_lines=ev.get("open_lines", 4),
                late_30=ev.get("late_30", 0),
                late_60=ev.get("late_60", 0),
                late_90=ev.get("late_90", 0),
            )
        elif "bank_statement" in ev_id:
            _lib.bank_statement(
                evidence_dir / f"{ev_id}.pdf",
                holder=spec["name"],
                bank=spec["bank"],
                issue_date=ev.get("issue_date", "2026-04-19"),
                avg_balance=ev["avg_balance"],
                closing=ev["closing"],
                period_start="2026-01-01",
                period_end="2026-03-31",
            )

    # Adversarial — same set for every case so judges can probe the Shield
    _lib.stale_payslip(
        adversarial_dir / "stale_payslip_2019.pdf",
        employee=spec["name"], employer=spec["employer"],
        gross=82000, net=68000,
    )
    _lib.unsigned_payslip(
        adversarial_dir / "unsigned_payslip.pdf",
        employee=spec["name"], gross=82000, net=68000,
    )
    _lib.implausible_payslip(
        adversarial_dir / "implausible_payslip.pdf",
        employee=spec["name"], employer=spec["employer"],
    )
    _lib.wrong_doc_type(adversarial_dir / "wrong_doc_type.pdf")

    # case.json — what scripts/seed.py reads
    (case_dir / "case.json").write_text(json.dumps({
        "name": spec["name"],
        "applicant_id": spec["applicant_id"],
        "application_id": spec["application_id"],
        "dob": spec["dob"],
        "email": spec["email"],
        "phone": spec.get("phone"),
        "amount": spec["amount"],
        "purpose": spec["purpose"],
        "story": spec.get("story", ""),
        "intake_features": spec["intake_features"],
        "intake_documents": [
            {"doc_type": "payslip", "file": "intake/payslip.pdf"},
            {"doc_type": "bank_statement", "file": "intake/bank_statement.pdf"},
            {"doc_type": "credit_report", "file": "intake/credit_report.pdf"},
        ],
        "evidence_catalog": [
            {"id": ev_id, "file": f"evidence/{ev_id}.pdf",
             "doc_type": _lib_doc_type(ev_id),
             "target_feature": _lib_target(ev_id)}
            for ev_id in spec.get("evidence", {})
        ],
        "adversarial_catalog": [
            {"id": "stale_payslip_2019", "file": "adversarial/stale_payslip_2019.pdf", "doc_type": "payslip", "target_feature": "MonthlyIncome", "expected_failure": "freshness"},
            {"id": "unsigned_payslip", "file": "adversarial/unsigned_payslip.pdf", "doc_type": "payslip", "target_feature": "MonthlyIncome", "expected_failure": "issuer_present"},
            {"id": "implausible_payslip", "file": "adversarial/implausible_payslip.pdf", "doc_type": "payslip", "target_feature": "MonthlyIncome", "expected_failure": "plausibility_vs_baseline"},
            {"id": "wrong_doc_type", "file": "adversarial/wrong_doc_type.pdf", "doc_type": "payslip", "target_feature": "MonthlyIncome", "expected_failure": "doc_type_matches_claim"},
        ],
    }, indent=2))
    print(f"  built {name}: {spec['name']}  ({spec['application_id']})")


def _lib_doc_type(evidence_id: str) -> str:
    if "payslip" in evidence_id:
        return "payslip"
    if "credit_report" in evidence_id:
        return "credit_report"
    if "bank_statement" in evidence_id:
        return "bank_statement"
    return "payslip"


def _lib_target(evidence_id: str) -> str:
    if "credit_report" in evidence_id:
        return "RevolvingUtilizationOfUnsecuredLines"
    if "bank_statement" in evidence_id:
        return "MonthlyIncome"
    return "MonthlyIncome"


def main() -> None:
    print("Generating case fixtures…")
    for name, spec in CASES.items():
        build_case(name, spec)
    print(f"\nDone. {len(CASES)} cases at {HERE}")


if __name__ == "__main__":
    main()
