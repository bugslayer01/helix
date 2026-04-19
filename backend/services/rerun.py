"""Re-run the scoring model against the snapshot + applied proposals."""
from __future__ import annotations

import json
import time
from typing import Any

from backend import db as _db
from backend.services import audit_log
from shared.adapters import get_adapter


class ModelDriftError(Exception):
    """Raised when the live model version no longer matches the snapshot."""


def rerun_for_case(case_id: str) -> dict[str, Any]:
    with _db.conn() as c:
        case = c.execute("SELECT * FROM contest_cases WHERE id = ?", (case_id,)).fetchone()
        if not case:
            raise ValueError("case_not_found")
        proposals = c.execute(
            "SELECT * FROM proposals WHERE case_id = ? AND status IN ('validated')",
            (case_id,),
        ).fetchall()
        snapshot_features = json.loads(case["snapshot_features"])
        snapshot_shap = json.loads(case["snapshot_shap"])
        snapshot_decision = json.loads(case["snapshot_decision"])

    adapter = get_adapter("loans")
    if adapter.model_version_hash != case["model_version"]:
        audit_log.append(
            case_id,
            "model_drift",
            {"snapshot_version": case["model_version"], "live_version": adapter.model_version_hash},
        )
        raise ModelDriftError(f"Snapshot model {case['model_version']} ≠ live {adapter.model_version_hash}")

    new_features = dict(snapshot_features)
    applied_proposals: list[dict[str, Any]] = []
    for p in proposals:
        new_features[p["feature"]] = p["proposed_value"]
        applied_proposals.append({
            "id": p["id"],
            "feature": p["feature"],
            "original": p["original_value"],
            "proposed": p["proposed_value"],
            "evidence_id": p["evidence_id"],
        })

    prediction = adapter.predict(new_features)
    new_shap = adapter.explain(new_features)

    now = int(time.time())
    old_shap_by_feature = {row["feature"]: row for row in snapshot_shap}
    new_shap_by_feature = {row["feature"]: row for row in new_shap}

    delta: list[dict[str, Any]] = []
    for p in applied_proposals:
        old_row = old_shap_by_feature.get(p["feature"], {})
        new_row = new_shap_by_feature.get(p["feature"], {})
        delta.append({
            "feature": p["feature"],
            "display_name": old_row.get("display_name") or p["feature"],
            "old": p["original"],
            "new": p["proposed"],
            "evidence_id": p["evidence_id"],
            "contribution_old": old_row.get("contribution", 0),
            "contribution_new": new_row.get("contribution", 0),
        })

    old_verdict = snapshot_decision.get("verdict")
    new_verdict = prediction["decision"]
    outcome = "flipped" if new_verdict != old_verdict else "held"

    status = "verdict_flipped" if outcome == "flipped" else "verdict_held"
    with _db.conn() as c:
        c.execute(
            "UPDATE contest_cases SET status = ? WHERE id = ?",
            (status, case_id),
        )
        for p in applied_proposals:
            c.execute(
                "UPDATE proposals SET status = 'applied' WHERE id = ?",
                (p["id"],),
            )

    audit_log.append(
        case_id,
        "model_reran",
        {
            "new_prob_bad": prediction["prob_bad"],
            "new_verdict": new_verdict,
            "num_proposals": len(applied_proposals),
        },
    )
    audit_log.append(case_id, "verdict_computed", {"outcome": outcome, "from": old_verdict, "to": new_verdict})

    return {
        "outcome": outcome,
        "new_verdict": new_verdict,
        "new_prob_bad": prediction["prob_bad"],
        "new_features": new_features,
        "new_shap": new_shap,
        "delta": delta,
        "model_version": adapter.model_version_hash,
        "old_verdict": old_verdict,
        "completed_at": now,
    }
