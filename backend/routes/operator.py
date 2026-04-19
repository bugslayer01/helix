"""Recourse internal operator console — contest case inspection."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from backend import db as _db
from backend.services import audit_log

router = APIRouter(prefix="/api/v1/operator", tags=["operator"])


@router.get("/cases")
def list_cases(limit: int = 50) -> dict:
    with _db.conn() as c:
        rows = c.execute(
            """
            SELECT id, customer_id, external_case_id, external_ref, applicant_display,
                   status, created_at, closed_at
            FROM contest_cases ORDER BY created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {"cases": [dict(r) for r in rows]}


@router.get("/cases/{case_id}")
def case_detail(case_id: str) -> dict:
    with _db.conn() as c:
        case = c.execute("SELECT * FROM contest_cases WHERE id = ?", (case_id,)).fetchone()
        if not case:
            raise HTTPException(status_code=404, detail={"error": {"code": "not_found", "message": "Unknown case."}})
        evidence = c.execute(
            """
            SELECT e.id, e.target_feature, e.doc_type, e.extracted_value, e.sha256, e.uploaded_at,
                   v.overall, v.summary
            FROM evidence e
            LEFT JOIN evidence_validations v ON v.evidence_id = e.id
            WHERE e.case_id = ? ORDER BY e.uploaded_at
            """,
            (case_id,),
        ).fetchall()
        proposals = c.execute(
            "SELECT id, feature, original_value, proposed_value, evidence_id, status FROM proposals WHERE case_id = ?",
            (case_id,),
        ).fetchall()
        webhooks = c.execute(
            "SELECT id, new_decision, new_prob_bad, attempts, delivered_at, last_error FROM verdict_webhooks WHERE case_id = ? ORDER BY rowid",
            (case_id,),
        ).fetchall()

    return {
        "case": {
            "id": case["id"],
            "customer_id": case["customer_id"],
            "external_case_id": case["external_case_id"],
            "external_ref": case["external_ref"],
            "applicant_display": case["applicant_display"],
            "status": case["status"],
            "created_at": case["created_at"],
            "closed_at": case["closed_at"],
            "snapshot": {
                "features": json.loads(case["snapshot_features"]),
                "decision": json.loads(case["snapshot_decision"]),
                "shap": json.loads(case["snapshot_shap"]),
                "model_version": case["model_version"],
            },
        },
        "evidence": [dict(e) for e in evidence],
        "proposals": [dict(p) for p in proposals],
        "webhooks": [dict(w) for w in webhooks],
        "audit": audit_log.list_for_case(case_id),
    }
