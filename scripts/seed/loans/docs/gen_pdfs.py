"""Generate realistic demo PDFs for the Priya Sharma case.

Produces five PDFs in this directory:
- payslip_intake.pdf          (intake — net monthly ₹48,000)
- bank_statement_intake.pdf   (intake — avg balance ₹12,400)
- credit_report_intake.pdf    (intake — utilization 68%, score 702)
- payslip_evidence_new.pdf    (contest — promotion to ₹68,000)
- credit_report_evidence_new.pdf (contest — utilization 38%)

All PDFs have a real text layer so pdfplumber can extract fields without
needing the GLM-OCR fallback. They look like stylized templates so the demo
reads as a credible real document, not a blank page.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent


def _doc(path: Path, title: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(path),
        pagesize=A4,
        title=title,
        author="Helix Demo",
        subject="Loan intake document",
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


def payslip(path: Path, *, month: str, issue_date: str, gross: int, net: int):
    doc = _doc(path, "Payslip")
    s = _styles()
    story = [
        Paragraph("INFOSYS LIMITED", s["h1"]),
        Paragraph("Registered office · Electronic City, Bengaluru · CIN L85110KA1981PLC013115", s["dim"]),
        Spacer(1, 12),
        Paragraph(f"Monthly Payslip · {month}", s["h2"]),
        Spacer(1, 6),
        _table([
            ["Employee name", "Priya Sharma"],
            ["Employee ID", "INFY-8821-A"],
            ["Designation", "Senior Consultant"],
            ["PAN", "AXXPS1234K"],
            ["Pay period end", month + "-30"],
            ["Issue date", issue_date],
            ["Employer", "Infosys Limited"],
        ]),
        Spacer(1, 14),
        Paragraph("Earnings and deductions", s["h2"]),
        _table([
            ["Gross salary", f"INR{gross:,}"],
            ["Provident fund", "INR3,600"],
            ["Professional tax", "INR200"],
            ["Income tax (TDS)", f"INR{max(0, gross - net - 3800):,}"],
            ["Net salary", f"INR{net:,}"],
            ["Net monthly", f"INR{net:,}"],
        ]),
        Spacer(1, 18),
        Paragraph(
            f"This is a system-generated document. Net monthly of INR {net:,} has been credited "
            "to the employee's registered account. Signed by Payroll Operations, Infosys Ltd.",
            s["dim"],
        ),
    ]
    doc.build(story)


def bank_statement(path: Path, *, issue_date: str, avg_balance: int, closing: int):
    doc = _doc(path, "Bank Statement")
    s = _styles()
    story = [
        Paragraph("HDFC BANK LIMITED", s["h1"]),
        Paragraph("Bank name · HDFC Bank · IFSC HDFC0000123 · MICR 400240013", s["dim"]),
        Spacer(1, 10),
        Paragraph("Savings account statement", s["h2"]),
        _table([
            ["Account holder", "Priya Sharma"],
            ["Account number", "****4432"],
            ["Branch", "Bandra West"],
            ["Statement period", "2026-01-01 to 2026-03-31"],
            ["Issue date", issue_date],
            ["Issuer", "HDFC Bank"],
        ]),
        Spacer(1, 12),
        Paragraph("Summary", s["h2"]),
        _table([
            ["Opening balance", "INR92,410"],
            ["Closing balance", f"INR{closing:,}"],
            ["Average monthly balance", f"INR{avg_balance:,}"],
            ["Total credits", "INR1,84,000"],
            ["Total debits", "INR1,78,600"],
        ]),
        Spacer(1, 16),
        Paragraph(
            "Account has been active for 4+ years. Regular salary credits from "
            "Infosys Limited observed. Balance trend is stable. "
            "All account numbers are partially masked per RBI guidelines.",
            s["dim"],
        ),
    ]
    doc.build(story)


def credit_report(path: Path, *, issue_date: str, utilization_pct: int, score: int, open_lines: int):
    doc = _doc(path, "Credit Report")
    s = _styles()
    story = [
        Paragraph("EXPERIAN CREDIT INFORMATION REPORT", s["h1"]),
        Paragraph("Experian Credit Information Company of India · CIBIL/Equifax-compatible format", s["dim"]),
        Spacer(1, 10),
        Paragraph("Subject", s["h2"]),
        _table([
            ["Name", "Priya Sharma"],
            ["PAN", "AXXPS1234K"],
            ["Issuer", "Experian"],
            ["Report date", issue_date],
            ["Issue date", issue_date],
        ]),
        Spacer(1, 14),
        Paragraph("Headline metrics", s["h2"]),
        _table([
            ["Credit score", str(score)],
            ["Revolving utilization", f"{utilization_pct}%  (decimal {utilization_pct / 100:.2f})"],
            ["Open credit lines", str(open_lines)],
            ["30–59 days past due (last 2y)", "0"],
            ["60–89 days past due (last 2y)", "0"],
            ["90+ days past due (last 2y)", "0"],
            ["Real estate loans", "1"],
        ]),
        Spacer(1, 16),
        Paragraph(
            "This report is a credit bureau report. Values sourced from three trade lines "
            "(two unsecured credit cards, one home loan). Data refreshed on the issue date above. "
            "© Experian Credit Information Company of India Pvt. Ltd.",
            s["dim"],
        ),
    ]
    doc.build(story)


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    # Intake docs — reflect the pre-contest reality
    payslip(HERE / "payslip_intake.pdf", month="2026-03", issue_date="2026-03-31", gross=62000, net=48000)
    bank_statement(HERE / "bank_statement_intake.pdf", issue_date="2026-04-03", avg_balance=12400, closing=14900)
    credit_report(HERE / "credit_report_intake.pdf", issue_date="2026-04-01", utilization_pct=68, score=702, open_lines=4)
    # Contest evidence — Priya's corrections
    payslip(HERE / "payslip_evidence_new.pdf", month="2026-04", issue_date=today, gross=82000, net=68000)
    credit_report(HERE / "credit_report_evidence_new.pdf", issue_date=today, utilization_pct=38, score=741, open_lines=4)
    print("Demo PDFs written to", HERE)


if __name__ == "__main__":
    main()
