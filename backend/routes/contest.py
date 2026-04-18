from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from adapters import get_adapter
from seed_cases import SEED_CASES
from services import audit_log, evidence_store
from services.anomaly_check import check_anomalies
from services.evidence_validator import run_validation

router = APIRouter(prefix="/contest", tags=["contest"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ContestRequest(BaseModel):
    case_id: str
    contest_path: str  # "correction" | "new_evidence"
    reason_category: str
    user_context: str | None = None
    updates: dict
    evidence_refs: list[dict] | None = None


class ProposalIn(BaseModel):
    feature: str
    form_key: str
    policy: str  # "user_editable" | "evidence_driven"
    proposed_value: float | None = None
    evidence_type: str | None = None
    evidence_filename: str | None = None
    evidence_hash: str | None = None


class ProposeRequest(BaseModel):
    case_id: str
    contest_path: str
    reason_category: str
    user_context: str | None = None
    proposals: list[ProposalIn] = Field(min_length=1)


class ApplyRequest(BaseModel):
    apply_rejected_as_skip: bool = False


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _apply_updates(adapter, features: dict, updates: dict) -> dict:
    """Merge form-keyed updates into model-keyed features."""
    merged = dict(features)
    form_map = getattr(adapter, "form_key_map", {}) or getattr(adapter, "FORM_KEY_MAP", {})
    for key, raw in updates.items():
        model_key = form_map.get(key, key)
        try:
            v = float(raw)
        except (TypeError, ValueError):
            continue
        if model_key in ("DebtRatio", "RevolvingUtilizationOfUnsecuredLines") and v > 1:
            v = v / 100.0
        merged[model_key] = v
    return merged


def _shap_snapshot(shap_values: list[dict]) -> list[dict]:
    return [
        {
            "feature": r["feature"],
            "display_name": r["display_name"],
            "value": r.get("value"),
            "value_display": r.get("value_display", str(r.get("value"))),
            "contribution": r["contribution"],
            "contestable": r["contestable"],
            "protected": r["protected"],
        }
        for r in shap_values
    ]


def _build_outcome(
    case_id: str,
    contest_path: str,
    reason_category: str,
    adapter,
    original: dict,
    updates: dict,
    evidence_refs: list[dict] | None,
    audit_action: str,
) -> dict[str, Any]:
    """Shared re-run / audit logic used by both the legacy and new apply paths."""
    explain_before = {**original, "_case_id": case_id}
    before_pred = adapter.predict(original)
    before_shap = adapter.explain(explain_before)

    updated = _apply_updates(adapter, original, updates)
    anomalies = check_anomalies(case_id, original, updates, adapter.feature_schema())

    if anomalies:
        entry = audit_log.append(
            case_id=case_id,
            action="contest_anomaly",
            title="Contest flagged for review",
            subtitle=f"anomaly: {', '.join(anomalies)}",
            payload={"anomaly_flags": anomalies, "updates": updates},
            kind="warning",
        )
        return {
            "case_id": case_id,
            "contest_path": contest_path,
            "before": {
                "decision": before_pred["decision"],
                "confidence": before_pred["confidence"],
                "shap_values": _shap_snapshot(before_shap),
            },
            "after": None,
            "delta": None,
            "anomaly_flags": anomalies,
            "status": "queued_for_human_review",
            "audit_entry_id": entry["id"],
            "audit_hash": entry["hash"],
        }

    after_pred = adapter.predict(updated)
    explain_after = {**updated, "_case_id": case_id}
    after_shap = adapter.explain(explain_after)

    before_by_key = {r["feature"]: r for r in before_shap}
    after_by_key = {r["feature"]: r for r in after_shap}
    deltas: list[dict] = []
    for key in before_by_key:
        b = before_by_key[key]
        a = after_by_key.get(key, b)
        deltas.append(
            {
                "feature": key,
                "display_name": b["display_name"],
                "old_value": b.get("value"),
                "new_value": a.get("value"),
                "old_value_display": b.get("value_display"),
                "new_value_display": a.get("value_display"),
                "old_contribution": b["contribution"],
                "new_contribution": a["contribution"],
                "contribution_delta": round(
                    a["contribution"] - b["contribution"], 4
                ),
            }
        )

    entry = audit_log.append(
        case_id=case_id,
        action=audit_action,
        title=f"Re-evaluated · {after_pred['decision'].title()}",
        subtitle=(
            f"{reason_category} · confidence "
            f"{before_pred['confidence']:.2f} → {after_pred['confidence']:.2f}"
        ),
        payload={
            "contest_path": contest_path,
            "reason_category": reason_category,
            "updates": updates,
            "evidence_refs": evidence_refs or [],
        },
        kind="success" if after_pred["decision"] == "approved" else "info",
    )

    return {
        "case_id": case_id,
        "contest_path": contest_path,
        "before": {
            "decision": before_pred["decision"],
            "confidence": before_pred["confidence"],
            "shap_values": _shap_snapshot(before_shap),
        },
        "after": {
            "decision": after_pred["decision"],
            "confidence": after_pred["confidence"],
            "shap_values": _shap_snapshot(after_shap),
        },
        "delta": {
            "decision_flipped": before_pred["decision"] != after_pred["decision"],
            "confidence_change": round(
                after_pred["confidence"] - before_pred["confidence"], 4
            ),
            "feature_deltas": deltas,
        },
        "anomaly_flags": [],
        "audit_entry_id": entry["id"],
        "audit_hash": entry["hash"],
    }


def _schema_lookup(adapter) -> dict[str, dict[str, Any]]:
    return {row["feature"]: row for row in adapter.feature_schema()}


# ---------------------------------------------------------------------------
# Legacy endpoint — apply immediately, no evidence validation.
# ---------------------------------------------------------------------------


@router.post("")
def contest(req: ContestRequest) -> dict:
    """Legacy "apply immediately" contest endpoint.

    WARNING: this bypasses evidence validation entirely — the updates land on
    the feature vector and the model re-runs on the same request. New callers
    should use /contest/propose → /contest/{id}/status → /contest/{id}/apply.
    """
    case = SEED_CASES.get(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Unknown case_id")

    adapter = get_adapter(case["domain"])
    return _build_outcome(
        case_id=req.case_id,
        contest_path=req.contest_path,
        reason_category=req.reason_category,
        adapter=adapter,
        original=case["features"],
        updates=req.updates,
        evidence_refs=req.evidence_refs,
        audit_action=f"contest_{req.contest_path}",
    )


# ---------------------------------------------------------------------------
# Stage 1 — propose
# ---------------------------------------------------------------------------


@router.post("/propose")
async def propose(req: ProposeRequest) -> dict:
    case = SEED_CASES.get(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Unknown case_id")

    adapter = get_adapter(case["domain"])
    schema = _schema_lookup(adapter)

    errors: list[dict[str, Any]] = []
    for p in req.proposals:
        feat_schema = schema.get(p.feature)
        if feat_schema is None:
            errors.append({"feature": p.feature, "reason": "unknown_feature"})
            continue

        policy = feat_schema["correction_policy"]
        if policy == "locked":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "locked_feature",
                    "message": f"Feature {p.feature!r} is locked and cannot be contested",
                    "feature": p.feature,
                },
            )

        if p.policy != policy:
            errors.append(
                {
                    "feature": p.feature,
                    "reason": f"policy_mismatch (schema says {policy!r}, client sent {p.policy!r})",
                }
            )
            continue

        allowed_evidence = feat_schema.get("evidence_types") or []
        if policy == "user_editable":
            if p.proposed_value is None:
                errors.append(
                    {"feature": p.feature, "reason": "proposed_value_required"}
                )
                continue
            lo, hi = feat_schema.get("min"), feat_schema.get("max")
            val = float(p.proposed_value)
            if lo is not None and val < float(lo):
                errors.append(
                    {
                        "feature": p.feature,
                        "reason": f"proposed_value_below_min ({val} < {lo})",
                    }
                )
                continue
            if hi is not None and val > float(hi):
                errors.append(
                    {
                        "feature": p.feature,
                        "reason": f"proposed_value_above_max ({val} > {hi})",
                    }
                )
                continue
            if not p.evidence_type:
                errors.append(
                    {"feature": p.feature, "reason": "evidence_type_required"}
                )
                continue
            if allowed_evidence and p.evidence_type not in allowed_evidence:
                errors.append(
                    {
                        "feature": p.feature,
                        "reason": f"evidence_type_not_allowed (got {p.evidence_type!r}, allowed {allowed_evidence})",
                    }
                )
                continue

        elif policy == "evidence_driven":
            if p.proposed_value is not None:
                errors.append(
                    {
                        "feature": p.feature,
                        "reason": "proposed_value_not_allowed_for_evidence_driven",
                    }
                )
                continue
            if not p.evidence_type:
                errors.append(
                    {"feature": p.feature, "reason": "evidence_type_required"}
                )
                continue
            if allowed_evidence and p.evidence_type not in allowed_evidence:
                errors.append(
                    {
                        "feature": p.feature,
                        "reason": f"evidence_type_not_allowed (got {p.evidence_type!r}, allowed {allowed_evidence})",
                    }
                )
                continue

    if errors:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_proposals", "failures": errors},
        )

    contest = evidence_store.create_contest(
        case_id=req.case_id,
        contest_path=req.contest_path,
        reason_category=req.reason_category,
        user_context=req.user_context,
        proposals=[p.model_dump() for p in req.proposals],
    )

    entry = audit_log.append(
        case_id=req.case_id,
        action="evidence_submitted",
        title="Evidence submitted for validation",
        subtitle=f"{len(contest['proposals'])} proposal(s) · {req.reason_category}",
        payload={
            "contest_id": contest["id"],
            "contest_path": req.contest_path,
            "proposals": [
                {"feature": p["feature"], "policy": p["policy"]}
                for p in contest["proposals"]
            ],
        },
        kind="info",
    )

    asyncio.create_task(run_validation(contest["id"]))

    return {
        "contest_id": contest["id"],
        "status": "validating",
        "proposals": [
            {
                "feature": p["feature"],
                "status": p["status"],
                "estimated_validation_seconds": 2,
            }
            for p in contest["proposals"]
        ],
        "audit_entry_id": entry["id"],
        "audit_hash": entry["hash"],
    }


# ---------------------------------------------------------------------------
# Stage 2.5 — status polling
# ---------------------------------------------------------------------------


@router.get("/{contest_id}/status")
def status(contest_id: str) -> dict:
    contest = evidence_store.get_contest(contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="Unknown contest_id")
    # Only recompute when the terminal "applied" state has not been reached —
    # "applied" is set by the apply endpoint and should stick.
    agg = contest["status"]
    if agg != "applied":
        agg = evidence_store.compute_aggregate_status(contest["proposals"])
    return {
        "contest_id": contest["id"],
        "case_id": contest["case_id"],
        "status": agg,
        "proposals": [
            {
                "feature": p["feature"],
                "form_key": p["form_key"],
                "status": p["status"],
                "resolved_value": p["resolved_value"],
                "validation_note": p["validation_note"],
            }
            for p in contest["proposals"]
        ],
    }


# ---------------------------------------------------------------------------
# Stage 3 — apply
# ---------------------------------------------------------------------------


@router.post("/{contest_id}/apply")
def apply_contest(contest_id: str, body: ApplyRequest | None = None) -> dict:
    contest = evidence_store.get_contest(contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="Unknown contest_id")

    if contest["status"] == "applied":
        raise HTTPException(
            status_code=400,
            detail={"error": "already_applied", "status": "applied"},
        )

    agg = evidence_store.compute_aggregate_status(contest["proposals"])
    apply_rejected_as_skip = bool(body.apply_rejected_as_skip) if body else False

    if agg == "validating":
        raise HTTPException(
            status_code=400,
            detail={"error": "not_ready", "status": agg},
        )
    if agg == "rejected":
        raise HTTPException(
            status_code=400,
            detail={"error": "all_rejected", "status": agg},
        )
    if agg == "partially_rejected" and not apply_rejected_as_skip:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "partially_rejected",
                "status": agg,
                "hint": "pass {\"apply_rejected_as_skip\": true} to apply the validated subset",
            },
        )

    case = SEED_CASES.get(contest["case_id"])
    if case is None:
        raise HTTPException(status_code=404, detail="Unknown case_id")
    adapter = get_adapter(case["domain"])

    # Build the updates dict from validated proposals (form_key → resolved_value).
    updates: dict[str, float] = {}
    evidence_refs: list[dict[str, Any]] = []
    for p in contest["proposals"]:
        if p["status"] != "validated":
            continue
        if p["resolved_value"] is None:
            continue
        updates[p["form_key"]] = float(p["resolved_value"])
        evidence_refs.append(
            {
                "feature": p["feature"],
                "evidence_type": p["evidence_type"],
                "evidence_filename": p["evidence_filename"],
                "evidence_hash": p["evidence_hash"],
            }
        )

    result = _build_outcome(
        case_id=contest["case_id"],
        contest_path=contest["contest_path"],
        reason_category=contest["reason_category"],
        adapter=adapter,
        original=case["features"],
        updates=updates,
        evidence_refs=evidence_refs,
        audit_action=f"contest_{contest['contest_path']}_applied",
    )
    result["contest_id"] = contest["id"]
    result["applied_status"] = agg  # "validated" or "partially_rejected"

    evidence_store.set_contest_status(contest["id"], "applied")
    return result
