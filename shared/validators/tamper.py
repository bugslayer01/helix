"""Check 9 — text layer vs rendered OCR divergence.

If the PDF's underlying text layer disagrees with GLM-OCR's read of the rendered
image, someone likely edited the doc in place (Acrobat "Edit Text" etc.). The
extractor already holds both reads via the router; here we diff the load-bearing
numeric fields.
"""
from __future__ import annotations

import re

from .types import CheckResult, EvidenceContext

_NUMBER = re.compile(r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")
_DIVERGENCE_THRESHOLD = 0.10  # 10%


def _extract_biggest_number(text: str) -> float | None:
    if not text:
        return None
    best = None
    for m in _NUMBER.finditer(text):
        raw = m.group(0).replace(",", "")
        try:
            v = float(raw)
        except ValueError:
            continue
        if best is None or abs(v) > abs(best):
            best = v
    return best


def _find_closest_number(text: str, target: float) -> float | None:
    """Return the parseable number from ``text`` closest in magnitude to ``target``."""
    if not text or target is None:
        return None
    closest: float | None = None
    closest_dist = float("inf")
    for m in _NUMBER.finditer(text):
        raw = m.group(0).replace(",", "")
        try:
            v = float(raw)
        except ValueError:
            continue
        if abs(v) < 1:
            continue
        dist = abs(v - target)
        if dist < closest_dist:
            closest_dist = dist
            closest = v
    return closest


def check(ctx: EvidenceContext) -> CheckResult:
    # If extraction came from the pdfplumber template, the text layer IS the
    # source — there's nothing to diverge from since GLM-OCR wasn't run.
    if ctx.extraction_source.startswith("template"):
        return CheckResult(
            name="text_vs_render",
            passed=True,
            severity="low",
            detail="Extraction sourced from PDF text layer; no rendered-vs-text divergence possible.",
        )
    fields = ctx.extraction_fields or {}
    rendered_value = ctx.claimed_value
    if rendered_value is None:
        return CheckResult(
            name="text_vs_render",
            passed=True,
            severity="low",
            detail="No numeric value to cross-check.",
        )
    text_value = _find_closest_number(ctx.extraction_text_layer, rendered_value)
    if text_value is None:
        return CheckResult(
            name="text_vs_render",
            passed=True,
            severity="low",
            detail="No parseable numbers in text layer; skipping text-vs-render diff.",
        )
    denom = max(abs(rendered_value), abs(text_value), 1.0)
    diff = abs(rendered_value - text_value) / denom
    if diff <= _DIVERGENCE_THRESHOLD:
        return CheckResult(
            name="text_vs_render",
            passed=True,
            severity="low",
            detail=f"Text layer and rendered OCR agree (within {diff*100:.1f}%).",
            data={"text_value": text_value, "rendered_value": rendered_value},
        )
    return CheckResult(
        name="text_vs_render",
        passed=False,
        severity="high",
        detail=(
            f"Text layer reads {text_value} but rendered OCR reads {rendered_value}. "
            f"Divergence {diff*100:.1f}% suggests an in-place edit."
        ),
        data={"text_value": text_value, "rendered_value": rendered_value, "divergence": diff},
    )
