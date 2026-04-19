"""Shared PDF builders for case fixtures. Heavier templates than gen_pdfs.py.

Each builder writes a real text-layer PDF using reportlab. All monetary values
print as ``INR <n>`` so the templates parser locks on without unicode quirks.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _doc(path: Path, title: str) -> SimpleDocTemplate:
    path.parent.mkdir(parents=True, exist_ok=True)
    return SimpleDocTemplate(
        str(path),
        pagesize=A4,
        title=title,
        author="Helix Demo Fixtures",
        subject="Loan demo document",
        creator="ReportLab",
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
    )


def _styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=18, spaceAfter=4, textColor=colors.HexColor("#0E4A44")),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12, spaceAfter=2),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=10, spaceAfter=2),
        "dim": ParagraphStyle("dim", parent=base["Normal"], fontSize=9, textColor=colors.HexColor("#5D6F6C")),
    }


def _table(rows: list[list[str]]) -> Table:
    t = Table(rows, hAlign="LEFT", colWidths=[65 * mm, 90 * mm])
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#5D6F6C")),
            ]
        )
    )
    return t


def payslip(
    path: Path,
    *,
    employee: str,
    employer: str,
    pan: str,
    period_month: str,
    issue_date: str,
    gross: int,
    net: int,
    designation: str = "Senior Consultant",
    suppress_employer_line: bool = False,
):
    doc = _doc(path, "Payslip")
    s = _styles()
    rows = [
        ["Employee name", employee],
        ["Employee ID", "EMP-" + pan[-6:]],
        ["Designation", designation],
        ["PAN", pan],
        ["Issue date", issue_date],
        ["Pay period end", period_month + "-28"],
    ]
    if not suppress_employer_line:
        rows.append(["Employer", employer])
    story = [
        Paragraph(employer.upper(), s["h1"]),
        Paragraph(f"Registered office · India · monthly payslip", s["dim"]),
        Spacer(1, 12),
        Paragraph(f"Monthly Payslip · {period_month}", s["h2"]),
        Spacer(1, 6),
        _table(rows),
        Spacer(1, 14),
        Paragraph("Earnings and deductions", s["h2"]),
        _table([
            ["Gross salary", f"INR {gross:,}"],
            ["Provident fund", f"INR {int(gross * 0.06):,}"],
            ["Professional tax", "INR 200"],
            ["Income tax (TDS)", f"INR {max(0, gross - net - int(gross * 0.06) - 200):,}"],
            ["Net salary", f"INR {net:,}"],
            ["Net monthly", f"INR {net:,}"],
        ]),
        Spacer(1, 18),
        Paragraph(
            f"This is a system-generated document. Net monthly of INR {net:,} has been credited "
            f"to the employee's registered account. Signed by Payroll Operations, {employer}.",
            s["dim"],
        ),
    ]
    doc.build(story)


def bank_statement(
    path: Path,
    *,
    holder: str,
    bank: str,
    issue_date: str,
    avg_balance: int,
    closing: int,
    period_start: str,
    period_end: str,
):
    doc = _doc(path, "Bank Statement")
    s = _styles()
    story = [
        Paragraph(bank.upper(), s["h1"]),
        Paragraph(f"Bank name · {bank} · IFSC HDFC0000123 · MICR 400240013", s["dim"]),
        Spacer(1, 10),
        Paragraph("Savings account statement", s["h2"]),
        _table([
            ["Account holder", holder],
            ["Account number", "****4432"],
            ["Branch", "Bandra West"],
            ["Statement period", f"{period_start} to {period_end}"],
            ["Issue date", issue_date],
            ["Issuer", bank],
        ]),
        Spacer(1, 12),
        Paragraph("Summary", s["h2"]),
        _table([
            ["Opening balance", f"INR {int(avg_balance * 0.8):,}"],
            ["Closing balance", f"INR {closing:,}"],
            ["Average monthly balance", f"INR {avg_balance:,}"],
            ["Total credits", f"INR {avg_balance * 14:,}"],
            ["Total debits", f"INR {avg_balance * 13:,}"],
        ]),
        Spacer(1, 16),
        Paragraph(
            "Account active for 4+ years. Regular salary credits observed. "
            "Balance trend stable. Account numbers partially masked per RBI guidelines.",
            s["dim"],
        ),
    ]
    doc.build(story)


def credit_report(
    path: Path,
    *,
    holder: str,
    bureau: str,
    issue_date: str,
    utilization_pct: int,
    score: int,
    open_lines: int = 4,
    late_30: int = 0,
    late_60: int = 0,
    late_90: int = 0,
    real_estate: int = 1,
):
    doc = _doc(path, "Credit Report")
    s = _styles()
    story = [
        Paragraph(f"{bureau.upper()} CREDIT INFORMATION REPORT", s["h1"]),
        Paragraph(f"{bureau} Credit Information Company of India · CIBIL/Equifax-compatible format", s["dim"]),
        Spacer(1, 10),
        Paragraph("Subject", s["h2"]),
        _table([
            ["Name", holder],
            ["PAN", "AXXPS1234K"],
            ["Issuer", bureau],
            ["Report date", issue_date],
            ["Issue date", issue_date],
        ]),
        Spacer(1, 14),
        Paragraph("Headline metrics", s["h2"]),
        _table([
            ["Credit score", str(score)],
            ["Revolving utilization", f"{utilization_pct}%  (decimal {utilization_pct / 100:.2f})"],
            ["Open credit lines", str(open_lines)],
            ["30–59 days past due (last 2y)", str(late_30)],
            ["60–89 days past due (last 2y)", str(late_60)],
            ["90+ days past due (last 2y)", str(late_90)],
            ["Real estate loans", str(real_estate)],
        ]),
        Spacer(1, 16),
        Paragraph(
            f"This report is a credit bureau report. Values sourced from {open_lines} trade lines. "
            f"Data refreshed on the issue date above. © {bureau} Credit Information Company of India Pvt. Ltd.",
            s["dim"],
        ),
    ]
    doc.build(story)


def wrong_doc_type(path: Path):
    """Generate a *credit report* labeled as if it were a generic supporting doc.

    Trips ``doc_type_matches_claim`` when uploaded against a feature the doc
    type cannot support (e.g. uploading a credit report for ``MonthlyIncome``).
    """
    credit_report(
        path,
        holder="Generic Holder",
        bureau="Equifax",
        issue_date="2026-04-10",
        utilization_pct=42,
        score=698,
    )


def unsigned_payslip(path: Path, *, employee: str, gross: int, net: int):
    payslip(
        path,
        employee=employee,
        employer="Anonymous Pvt Ltd",
        pan="ZZZPS9999Z",
        period_month="2026-04",
        issue_date="2026-04-15",
        gross=gross,
        net=net,
        suppress_employer_line=True,
    )


def stale_payslip(path: Path, *, employee: str, employer: str, gross: int, net: int):
    payslip(
        path,
        employee=employee,
        employer=employer,
        pan="OLDPS0000O",
        period_month="2019-08",
        issue_date="2019-08-31",
        gross=gross,
        net=net,
    )


def implausible_payslip(path: Path, *, employee: str, employer: str):
    payslip(
        path,
        employee=employee,
        employer=employer,
        pan="BIGPS9999B",
        period_month="2026-04",
        issue_date="2026-04-15",
        gross=12_500_000,
        net=8_400_000,
    )
