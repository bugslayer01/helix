"""Shared types for all Evidence Shield checks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Severity = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    severity: Severity
    detail: str
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "detail": self.detail,
            **({"data": self.data} if self.data else {}),
        }


@dataclass(frozen=True)
class EvidenceContext:
    """Everything a check needs about the case + upload to make a decision."""
    case_id: str
    target_feature: str
    claimed_value: float | None
    prior_value: float | None
    upload_path: str
    upload_sha256: str
    doc_type_expected: str
    extraction_fields: dict[str, Any]
    extraction_text_layer: str
    extraction_confidence: float
    feature_bounds: tuple[float | None, float | None]
    realistic_delta_multiplier: float
    prior_evidence_for_feature: list[dict[str, Any]]
    replay_index_hit: dict[str, Any] | None
