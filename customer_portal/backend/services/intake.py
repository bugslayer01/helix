"""Intake — turns uploaded docs into a scoring-ready feature vector.

Flow:
1. Each uploaded doc is routed through ``shared.ocr.router.extract``.
2. A feature-assembly step fuses extracted fields from different doc types into
   a single feature dict the adapter can score.
3. For any feature the extractor failed to produce, a sensible default is
   sourced from ``loans_medians.json`` so the model still gets a complete vector.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shared.adapters import get_adapter
from shared.ocr import extract as ocr_extract

_FEATURE_FROM_DOC = {
    "payslip": {
        "MonthlyIncome": "net_monthly",
    },
    "bank_statement": {
        "MonthlyIncome": "average_monthly_balance",
    },
    "credit_report": {
        "RevolvingUtilizationOfUnsecuredLines": "revolving_utilization",
        "NumberOfOpenCreditLinesAndLoans": "open_lines",
        "NumberOfTimes90DaysLate": "times_90_days_late",
        "NumberOfTime30-59DaysPastDueNotWorse": "times_30_59_days_late",
        "NumberOfTime60-89DaysPastDueNotWorse": "times_60_89_days_late",
        "NumberRealEstateLoansOrLines": "real_estate_loans",
    },
}

_MEDIANS_PATH = Path(__file__).resolve().parents[3] / "shared" / "models" / "metadata" / "loans_medians.json"


def _load_medians() -> dict[str, float]:
    if not _MEDIANS_PATH.exists():
        return {}
    try:
        return json.loads(_MEDIANS_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def assemble_features(
    *,
    domain: str,
    applicant_dob: str,
    doc_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a complete feature vector for the adapter, fusing all intake docs."""
    medians = _load_medians()
    features: dict[str, Any] = dict(medians)  # start from population medians
    features["age"] = _age_from_dob(applicant_dob)
    features["NumberOfDependents"] = features.get("NumberOfDependents", 0)

    for record in doc_records:
        extracted = record.get("extracted") or {}
        doc_type = record.get("doc_type") or extracted.get("doc_type")
        mapping = _FEATURE_FROM_DOC.get(doc_type, {})
        for feature_name, extract_key in mapping.items():
            if extract_key in extracted and extracted[extract_key] is not None:
                features[feature_name] = extracted[extract_key]

    return features


def extract_doc(path: Path, doc_type: str, domain: str = "loans") -> dict[str, Any]:
    """Run OCR + template fallback and return extracted fields + text layer."""
    adapter = get_adapter(domain)
    prompt_spec = adapter.extract_prompt(doc_type)
    result = ocr_extract(
        path,
        expected_doc_type=doc_type,
        schema=prompt_spec.get("schema"),
        prompt=prompt_spec.get("prompt"),
    )
    return {
        "doc_type": doc_type,
        "extracted": result.fields,
        "text_layer": result.text_layer,
        "source": result.source,
        "confidence": result.confidence,
    }


def _age_from_dob(dob_iso: str) -> int:
    from datetime import date
    try:
        parts = [int(p) for p in dob_iso.split("-")]
        birth = date(parts[0], parts[1], parts[2])
    except Exception:
        return 30
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
