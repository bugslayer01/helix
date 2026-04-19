"""Cross-boundary case snapshot endpoint.

Recourse calls GET /api/v1/cases/{case_id} with the handoff JWT to fetch the
case state. This is the only endpoint Recourse needs to read case data —
everything subsequent happens inside Recourse's own DB.
"""
from __future__ import annotations

import hashlib
import json
import time

from fastapi import APIRouter, Header, HTTPException

from customer_portal.backend import db
from shared.jwt_utils import HandoffError, verify_handoff

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

_CASE_SALT = "helix-demo-salt"  # shared constant — production would be per-tenant


def _dob_hash(dob_iso: str) -> str:
    return "sha256:" + hashlib.sha256(f"{dob_iso}|{_CASE_SALT}".encode()).hexdigest()


@router.get("/{case_id}")
def get_case(case_id: str, authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"error": {"code": "missing_token", "message": "Authorization Bearer token required."}})
    token = authorization.split(None, 1)[1].strip()
    try:
        claims = verify_handoff(token)
    except HandoffError as exc:
        raise HTTPException(status_code=401, detail={"error": {"code": str(exc), "message": "JWT verification failed."}})
    if claims.case_id != case_id:
        raise HTTPException(status_code=409, detail={"error": {"code": "case_mismatch", "message": "JWT case_id does not match URL."}})

    with db.conn() as c:
        handoff = c.execute("SELECT * FROM contest_handoffs WHERE jti = ?", (claims.jti,)).fetchone()
        if not handoff:
            raise HTTPException(status_code=401, detail={"error": {"code": "unknown_jti", "message": "JTI not issued by LenderCo."}})
        if handoff["revoked_at"]:
            raise HTTPException(status_code=403, detail={"error": {"code": "revoked", "message": "Case was revoked."}})
        if handoff["expires_at"] < int(time.time()):
            raise HTTPException(status_code=401, detail={"error": {"code": "handoff_expired", "message": "Handoff expired."}})

        app_row = c.execute("SELECT * FROM applications WHERE id = ?", (case_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail={"error": {"code": "application_not_found", "message": "Unknown case."}})
        applicant = c.execute("SELECT * FROM applicants WHERE id = ?", (app_row["applicant_id"],)).fetchone()
        decision = c.execute(
            "SELECT * FROM decisions WHERE application_id = ? ORDER BY decided_at DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        scored = c.execute("SELECT * FROM scored_features WHERE application_id = ?", (case_id,)).fetchone()
        docs = c.execute(
            "SELECT id, doc_type, original_name, uploaded_at FROM intake_documents WHERE application_id = ? ORDER BY uploaded_at",
            (case_id,),
        ).fetchall()

    if not (decision and scored):
        raise HTTPException(status_code=409, detail={"error": {"code": "not_decided", "message": "Case has no decision yet."}})

    return {
        "case_id": case_id,
        "external_ref": case_id,
        "applicant": {
            "display_name": applicant["full_name"],
            "dob_hash": _dob_hash(applicant["dob"]),
        },
        "decision": {
            "verdict": decision["verdict"],
            "prob_bad": decision["prob_bad"],
            "decided_at": decision["decided_at"],
        },
        "features": json.loads(scored["feature_vector"]),
        "shap": json.loads(decision["shap_json"]),
        "top_reasons": json.loads(decision["top_reasons"]),
        "model_version": scored["model_version"],
        "intake_docs": [dict(d) for d in docs],
    }
