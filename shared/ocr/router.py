"""Routes an extraction request to the fastest reliable path.

Order:
1. pdfplumber template parser for the expected doc_type. If confidence ≥ threshold,
   return it. Zero model cost; fully deterministic.
2. GLM-OCR via Ollama. Works on any PDF or image, including scans with no text layer.

Callers supply a ``doc_type`` (payslip / bank_statement / credit_report) and a JSON
schema describing the fields to extract. The router attaches both the extracted
fields AND the raw text layer (for downstream tamper checks).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import extract as glm
from . import templates

_TEMPLATE_CONFIDENCE_THRESHOLD = 0.67


@dataclass
class ExtractionResult:
    doc_type: str | None
    fields: dict[str, Any]
    text_layer: str
    source: str  # "template" | "glm-ocr"
    confidence: float
    notes: list[str] = field(default_factory=list)


def _default_schema(doc_type: str) -> dict[str, Any]:
    """Minimal JSON schema if the adapter doesn't supply one. Keeps GLM-OCR happy."""
    base_schema = {
        "type": "object",
        "properties": {
            "doc_type": {"type": "string"},
            "issuer": {"type": "string"},
            "issue_date": {"type": "string", "description": "ISO-8601 date YYYY-MM-DD"},
        },
        "required": ["doc_type"],
    }
    if doc_type == "payslip":
        base_schema["properties"].update({
            "employer": {"type": "string"},
            "employee_name": {"type": "string"},
            "gross_monthly": {"type": "number"},
            "net_monthly": {"type": "number"},
            "pay_period_end": {"type": "string"},
        })
    elif doc_type == "bank_statement":
        base_schema["properties"].update({
            "account_holder": {"type": "string"},
            "bank": {"type": "string"},
            "closing_balance": {"type": "number"},
            "average_monthly_balance": {"type": "number"},
            "statement_period_start": {"type": "string"},
            "statement_period_end": {"type": "string"},
        })
    elif doc_type == "credit_report":
        base_schema["properties"].update({
            "bureau": {"type": "string"},
            "credit_score": {"type": "integer"},
            "revolving_utilization": {"type": "number", "description": "0..1"},
            "open_lines": {"type": "integer"},
            "report_date": {"type": "string"},
        })
    return base_schema


def _default_prompt(doc_type: str) -> str:
    return (
        f"You are extracting structured fields from a {doc_type.replace('_', ' ')}."
        " Return ONLY the JSON object matching the provided schema. Use numbers for"
        " monetary values (no currency symbols). Use ISO 8601 YYYY-MM-DD for all"
        " dates. If a field is absent, omit it."
    )


def extract(
    path: Path,
    expected_doc_type: str,
    *,
    schema: dict[str, Any] | None = None,
    prompt: str | None = None,
    force_glm: bool = False,
) -> ExtractionResult:
    """Return an ``ExtractionResult`` for ``path`` assuming ``expected_doc_type``."""
    text_layer = templates.extract_text_layer(path)

    if not force_glm:
        fast = templates.try_parse(path, expected_doc_type)
        if fast.confidence >= _TEMPLATE_CONFIDENCE_THRESHOLD:
            return ExtractionResult(
                doc_type=fast.fields.get("doc_type") or expected_doc_type,
                fields=fast.fields,
                text_layer=fast.text_layer or text_layer,
                source="template",
                confidence=fast.confidence,
                notes=list(fast.notes),
            )

    resolved_schema = schema or _default_schema(expected_doc_type)
    resolved_prompt = prompt or _default_prompt(expected_doc_type)
    try:
        fields = glm.extract_with_schema(path, prompt=resolved_prompt, json_schema=resolved_schema)
    except glm.GLMExtractError as exc:
        # Degrade gracefully: surface the template result even if weak, plus note.
        fast = templates.try_parse(path, expected_doc_type)
        return ExtractionResult(
            doc_type=fast.fields.get("doc_type") or expected_doc_type,
            fields=fast.fields,
            text_layer=text_layer,
            source="template-fallback",
            confidence=max(fast.confidence, 0.25),
            notes=[*fast.notes, f"glm_error: {exc}"],
        )

    confidence = 0.9 if fields else 0.4
    return ExtractionResult(
        doc_type=fields.get("doc_type") or expected_doc_type,
        fields=fields,
        text_layer=text_layer,
        source="glm-ocr",
        confidence=confidence,
    )
