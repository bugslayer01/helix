"""Check 8 — PDF metadata forensics."""
from __future__ import annotations

import re
from datetime import datetime, date
from pathlib import Path

from .types import CheckResult, EvidenceContext


def _parse_pdf_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    # Strip leading "D:" if present, drop timezone suffix.
    s = raw.lstrip("D:")
    m = re.match(r"(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?", s)
    if not m:
        return None
    y, mo, d, h, mi, se = (int(g) if g else 0 for g in m.groups())
    try:
        return datetime(y, mo, d, h or 0, mi or 0, se or 0)
    except ValueError:
        return None


_SUSPECT_CREATORS = {"canva", "google docs", "microsoft word", "libreoffice", "wps office", "pages"}


def check(ctx: EvidenceContext) -> CheckResult:
    path = Path(ctx.upload_path)
    if not path.exists() or path.suffix.lower() != ".pdf":
        return CheckResult(
            name="pdf_metadata_check",
            passed=True,
            severity="low",
            detail="Non-PDF upload; skipping PDF metadata forensics.",
        )
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return CheckResult(
            name="pdf_metadata_check",
            passed=True,
            severity="low",
            detail="pypdf unavailable; metadata forensics skipped.",
        )
    try:
        reader = PdfReader(str(path))
        meta = reader.metadata or {}
    except Exception as exc:  # malformed PDF
        return CheckResult(
            name="pdf_metadata_check",
            passed=False,
            severity="medium",
            detail=f"PDF metadata unreadable: {exc}.",
        )
    creator = str(meta.get("/Creator") or meta.get("/Producer") or "").lower()
    cdate = _parse_pdf_date(str(meta.get("/CreationDate"))) if meta.get("/CreationDate") else None
    mdate = _parse_pdf_date(str(meta.get("/ModDate"))) if meta.get("/ModDate") else None
    notes: list[str] = []
    severity: str = "low"
    passed = True

    # Issue date declared on doc face vs creation date.
    fields = ctx.extraction_fields or {}
    raw_issue = fields.get("issue_date") or fields.get("pay_period_end") or fields.get("report_date")
    issue_date = None
    if raw_issue:
        try:
            issue_date = datetime.fromisoformat(raw_issue).date()
        except ValueError:
            issue_date = None
    if issue_date and cdate and (cdate.date() - issue_date).days > 45:
        notes.append(f"created {(cdate.date() - issue_date).days}d after issue date")
        severity = "medium"
        passed = False

    if mdate and cdate and (mdate - cdate).total_seconds() > 86400:
        notes.append(f"modified {(mdate - cdate).days}d after creation")
        severity = severity if severity == "medium" else "medium"
        passed = False

    if any(s in creator for s in _SUSPECT_CREATORS):
        # low severity; many real docs are exported via these tools
        notes.append(f"creator tool: {creator!r}")
        if severity == "low":
            severity = "low"

    if not notes:
        return CheckResult(
            name="pdf_metadata_check",
            passed=True,
            severity="low",
            detail="Metadata coherent.",
            data={"creator": creator or None},
        )
    return CheckResult(
        name="pdf_metadata_check",
        passed=passed,
        severity=severity,  # type: ignore[arg-type]
        detail="; ".join(notes),
        data={"creator": creator or None},
    )
