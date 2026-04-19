"""LenderCo operator (internal CS agent) console. List + drill-down."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from customer_portal.backend import db

router = APIRouter(prefix="/api/v1/operator", tags=["operator"])


@router.get("/cases")
def list_cases(limit: int = 50) -> dict:
    with db.conn() as c:
        rows = c.execute(
            """
            SELECT a.id, a.status, a.amount, a.purpose, a.submitted_at, a.decided_at,
                   ap.full_name, ap.email,
                   d.verdict, d.prob_bad, d.source, d.decided_at AS decision_at
            FROM applications a
            JOIN applicants ap ON ap.id = a.applicant_id
            LEFT JOIN decisions d ON d.application_id = a.id
            ORDER BY a.submitted_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {"cases": [dict(r) for r in rows]}


@router.get("/cases/{app_id}")
def get_case(app_id: str) -> dict:
    with db.conn() as c:
        app_row = c.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail={"error": {"code": "not_found", "message": "Unknown application."}})
        applicant = c.execute("SELECT * FROM applicants WHERE id = ?", (app_row["applicant_id"],)).fetchone()
        decisions = c.execute(
            "SELECT * FROM decisions WHERE application_id = ? ORDER BY decided_at",
            (app_id,),
        ).fetchall()
        scored = c.execute("SELECT * FROM scored_features WHERE application_id = ?", (app_id,)).fetchone()
        docs = c.execute("SELECT * FROM intake_documents WHERE application_id = ?", (app_id,)).fetchall()
        handoffs = c.execute(
            "SELECT jti, issued_at, expires_at, revoked_at FROM contest_handoffs WHERE application_id = ?",
            (app_id,),
        ).fetchall()
    return {
        "application": dict(app_row),
        "applicant": dict(applicant),
        "scored_features": (
            {"feature_vector": json.loads(scored["feature_vector"]), "model_version": scored["model_version"], "scored_at": scored["scored_at"]}
            if scored
            else None
        ),
        "decisions": [
            {
                "id": d["id"],
                "verdict": d["verdict"],
                "prob_bad": d["prob_bad"],
                "source": d["source"],
                "decided_at": d["decided_at"],
                "shap": json.loads(d["shap_json"] or "[]"),
                "top_reasons": json.loads(d["top_reasons"] or "[]"),
            }
            for d in decisions
        ],
        "intake_documents": [
            {
                "id": d["id"],
                "doc_type": d["doc_type"],
                "original_name": d["original_name"],
                "sha256": d["sha256"],
                "uploaded_at": d["uploaded_at"],
            }
            for d in docs
        ],
        "contest_handoffs": [dict(h) for h in handoffs],
    }
