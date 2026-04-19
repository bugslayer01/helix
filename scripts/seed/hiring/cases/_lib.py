"""Generate plausible resume PDFs for hiring fixtures."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=20, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12, spaceAfter=2, textColor=colors.HexColor("#0E4A44")),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=10, spaceAfter=4, leading=14),
        "dim": ParagraphStyle("dim", parent=base["Normal"], fontSize=9, textColor=colors.HexColor("#5D6F6C")),
    }


def render_resume(path: Path, *, name: str, email: str, summary: str, experience: list[str], skills: list[str], education: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(path), pagesize=A4, title=f"{name} resume", author="Helix demo", rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    s = _styles()
    story = [
        Paragraph(name, s["h1"]),
        Paragraph(email, s["dim"]),
        Spacer(1, 12),
        Paragraph("Summary", s["h2"]),
        Paragraph(summary, s["body"]),
        Spacer(1, 8),
        Paragraph("Experience", s["h2"]),
    ]
    for e in experience:
        story.append(Paragraph(e, s["body"]))
    story += [
        Spacer(1, 8),
        Paragraph("Skills", s["h2"]),
        Paragraph(", ".join(skills), s["body"]),
        Spacer(1, 8),
        Paragraph("Education", s["h2"]),
        Paragraph(education, s["body"]),
    ]
    doc.build(story)
