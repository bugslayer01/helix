"""Hiring intake — read resume PDF text, call LLM via adapter, persist decision.

Uses pdfplumber for resume text (digital PDFs) and falls back to GLM-OCR if
text layer is empty. The hiring adapter then performs the LLM judgment.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shared.adapters import get_adapter
from shared.ocr import extract as ocr_extract


def extract_resume_text(path: Path) -> str:
    """Return the resume's text. Falls back to OCR on scanned PDFs."""
    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(path) as pdf:
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        if text.strip():
            return text
    except Exception:
        pass
    result = ocr_extract(path, expected_doc_type="resume")
    return result.text_layer or json.dumps(result.fields)


def score_application(jd_text: str, resume_text: str) -> dict[str, Any]:
    adapter = get_adapter("hiring")
    features = {"jd_text": jd_text, "resume_text": resume_text}
    pred = adapter.predict(features)
    shap = adapter.explain(features)
    top_reasons = []
    sign = -1 if pred["decision"] == "denied" else 1
    ranked = sorted(shap, key=lambda r: sign * r.get("contribution", 0))
    for row in ranked[:3]:
        top_reasons.append(
            f"{row['display_name']}: {row.get('jd_requirement', '')} (your: {row.get('value', '')})"
        )
    return {
        "verdict": pred["decision"],
        "prob_bad": pred["prob_bad"],
        "confidence": pred["confidence"],
        "shap": shap,
        "top_reasons": top_reasons,
        "model_version": adapter.model_version_hash,
    }
