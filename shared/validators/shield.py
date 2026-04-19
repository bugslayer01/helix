"""Orchestrator — runs all 10 Evidence Shield checks and produces a report."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from . import (
    baseline,
    bounds,
    cross_doc,
    doc_type,
    format_sanity,
    freshness,
    issuer,
    metadata_check,
    replay,
    tamper,
)
from .types import CheckResult, EvidenceContext

Overall = Literal["accepted", "flagged", "rejected"]

_CHECKS = (
    ("doc_type_matches_claim", doc_type.check),
    ("freshness", freshness.check),
    ("bounds", bounds.check),
    ("cross_doc_consistency", cross_doc.check),
    ("issuer_present", issuer.check),
    ("format_sanity", format_sanity.check),
    ("plausibility_vs_baseline", baseline.check),
    ("pdf_metadata_check", metadata_check.check),
    ("text_vs_render", tamper.check),
    ("replay", replay.check),
)


@dataclass(frozen=True)
class ValidationReport:
    overall: Overall
    summary: str
    checks: list[CheckResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "summary": self.summary,
            "checks": [c.to_dict() for c in self.checks],
        }


def _overall_from_checks(checks: list[CheckResult]) -> Overall:
    for c in checks:
        if not c.passed and c.severity == "high":
            return "rejected"
    for c in checks:
        if not c.passed and c.severity == "medium":
            return "flagged"
    return "accepted"


def _summarize(overall: Overall, checks: list[CheckResult]) -> str:
    failed = [c for c in checks if not c.passed]
    if overall == "accepted":
        return f"All 10 checks passed."
    if overall == "flagged":
        names = ", ".join(c.name for c in failed)
        return f"Accepted with flags: {names}. Operator review recommended."
    names = ", ".join(c.name for c in failed if c.severity == "high")
    return f"Rejected due to {names}."


def run_shield(ctx: EvidenceContext) -> ValidationReport:
    results: list[CheckResult] = []
    for _, fn in _CHECKS:
        try:
            results.append(fn(ctx))
        except Exception as exc:  # check bugs shouldn't kill the pipeline
            results.append(
                CheckResult(
                    name=fn.__module__.split(".")[-1],
                    passed=False,
                    severity="medium",
                    detail=f"Check raised {type(exc).__name__}: {exc}",
                )
            )
    overall = _overall_from_checks(results)
    return ValidationReport(overall=overall, summary=_summarize(overall, results), checks=results)
