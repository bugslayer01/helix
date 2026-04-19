"""Fast-path PDF parsing for digital documents with a recognizable text layer.

When the text layer exists and contains the expected anchors (e.g. "Net Salary",
"Total Amount"), regex extraction is near-instant and fully deterministic — no
model in the loop. The router tries templates first and falls back to GLM-OCR
when templates return a low-confidence result.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class TemplateResult:
    fields: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    text_layer: str = ""
    notes: list[str] = field(default_factory=list)


def extract_text_layer(path: Path) -> str:
    """Return concatenated text from every page of a digital PDF."""
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return ""
    try:
        with pdfplumber.open(path) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)
    except Exception:
        return ""


_CURRENCY_NUMBER = re.compile(r"(?:₹|INR|Rs\.?)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
_PLAIN_NUMBER = re.compile(r"([\d,]+(?:\.\d{1,2})?)")
_DATE_PATTERNS = [
    re.compile(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b"),
]


def _parse_number(raw: str) -> float | None:
    raw = raw.replace(",", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _scan_currency_after(text: str, anchor_pattern: str) -> float | None:
    pattern = re.compile(rf"{anchor_pattern}[^\n₹0-9]*({_CURRENCY_NUMBER.pattern}|{_PLAIN_NUMBER.pattern})", re.IGNORECASE)
    m = pattern.search(text)
    if not m:
        return None
    raw = m.group(2) or m.group(3)
    return _parse_number(raw) if raw else None


def _extract_issue_date(text: str) -> str | None:
    """Find the most recent-looking date on the doc. Returns ISO 8601 YYYY-MM-DD."""
    for pat in _DATE_PATTERNS:
        for match in pat.finditer(text):
            try:
                if len(match.group(1)) == 4:
                    y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
                else:
                    d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
                return datetime(y, m, d).date().isoformat()
            except ValueError:
                continue
    return None


def parse_payslip(text: str) -> TemplateResult:
    result = TemplateResult(text_layer=text)
    gross = _scan_currency_after(text, r"gross\s*(?:salary|pay)")
    net = _scan_currency_after(text, r"net\s*(?:salary|pay|amount)")
    issue_date = _extract_issue_date(text)
    employer = None
    employer_m = re.search(r"(?:employer|company)\s*[:\-]\s*([A-Z][A-Za-z0-9 .,&'-]{2,60})", text)
    if employer_m:
        employer = employer_m.group(1).strip()

    if gross:
        result.fields["gross_monthly"] = gross
    if net:
        result.fields["net_monthly"] = net
    if employer:
        result.fields["issuer"] = employer
    if issue_date:
        result.fields["issue_date"] = issue_date
    result.fields["doc_type"] = "payslip"

    # Confidence = fraction of expected anchors present.
    expected = 4
    present = sum(1 for k in ("net_monthly", "gross_monthly", "issuer", "issue_date") if k in result.fields)
    result.confidence = present / expected
    if net is None and gross is None:
        result.notes.append("no_salary_anchor")
    return result


def parse_bank_statement(text: str) -> TemplateResult:
    result = TemplateResult(text_layer=text)
    closing = _scan_currency_after(text, r"closing\s*balance")
    avg = _scan_currency_after(text, r"(?:average|avg)\s*(?:monthly\s*)?balance")
    issue_date = _extract_issue_date(text)
    issuer_m = re.search(r"(?:bank\s+name|issued\s+by|account\s+with|issuer)\s*[:\-·]*\s*([A-Z][A-Za-z0-9 .,&'-]{2,60})", text, re.IGNORECASE)
    if closing:
        result.fields["closing_balance"] = closing
    if avg:
        result.fields["average_monthly_balance"] = avg
    if issuer_m:
        result.fields["issuer"] = issuer_m.group(1).strip()
    if issue_date:
        result.fields["issue_date"] = issue_date
    result.fields["doc_type"] = "bank_statement"

    expected = 3
    present = sum(1 for k in ("closing_balance", "average_monthly_balance", "issuer") if k in result.fields)
    result.confidence = present / expected
    return result


def parse_credit_report(text: str) -> TemplateResult:
    result = TemplateResult(text_layer=text)
    util = None
    util_m = re.search(r"(?:utilization|utilisation)[^\d]{0,20}(\d{1,3})\s*%", text, re.IGNORECASE)
    if util_m:
        util = float(util_m.group(1)) / 100.0
    score = None
    score_m = re.search(r"(?:credit\s*score|cibil)\s*[:\-]?\s*(\d{3,4})", text, re.IGNORECASE)
    if score_m:
        score = int(score_m.group(1))
    issue_date = _extract_issue_date(text)
    if util is not None:
        result.fields["revolving_utilization"] = util
    if score is not None:
        result.fields["credit_score"] = score
    if issue_date:
        result.fields["issue_date"] = issue_date
    result.fields["doc_type"] = "credit_report"
    result.fields["issuer"] = result.fields.get("issuer") or _detect_bureau(text)

    expected = 3
    present = sum(1 for k in ("revolving_utilization", "credit_score", "issuer") if k in result.fields)
    result.confidence = present / expected
    return result


def _detect_bureau(text: str) -> str | None:
    for name in ("Experian", "Equifax", "TransUnion", "CIBIL", "CRIF"):
        if name.lower() in text.lower():
            return name
    return None


PARSERS = {
    "payslip": parse_payslip,
    "bank_statement": parse_bank_statement,
    "credit_report": parse_credit_report,
}


def try_parse(path: Path, expected_doc_type: str) -> TemplateResult:
    """Run the template parser for the expected doc type against a digital PDF."""
    text = extract_text_layer(path)
    if not text.strip():
        return TemplateResult(confidence=0.0, notes=["no_text_layer"])
    parser = PARSERS.get(expected_doc_type)
    if parser is None:
        return TemplateResult(text_layer=text, confidence=0.0, notes=["no_template_for_doc_type"])
    return parser(text)
