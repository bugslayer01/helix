"""Evidence upload + inspection endpoints for a live contest session."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend import db as _db
from backend.routes.handoff import require_session
from backend.services import evidence_pipeline

router = APIRouter(prefix="/api/v1/contest", tags=["contest-evidence"])


@router.post("/evidence")
async def upload_evidence(
    session: dict = Depends(require_session),
    target_feature: str = Form(...),
    doc_type: str = Form(...),
    rebuttal_text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
) -> dict:
    blob = b""
    if file is not None:
        blob = await file.read()
    if not blob and not rebuttal_text:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "empty_upload", "message": "Provide a file or rebuttal text."}},
        )
    if not blob:
        # Text-only rebuttal — fabricate a placeholder doc so the
        # pipeline still records an evidence row with a unique sha.
        blob = (rebuttal_text or "").encode("utf-8")
    try:
        return evidence_pipeline.process_upload(
            case_id=session["case_id"],
            target_feature=target_feature,
            doc_type=doc_type,
            original_name=file.filename if file else "rebuttal.txt",
            blob=blob,
            rebuttal_text=rebuttal_text,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": str(exc), "message": "Upload failed."}},
        )


@router.get("/evidence")
def list_evidence(session: dict = Depends(require_session)) -> dict:
    with _db.conn() as c:
        rows = c.execute(
            """
            SELECT e.id, e.target_feature, e.doc_type, e.extracted_json, e.extracted_value, e.uploaded_at,
                   v.overall, v.summary, v.checks_json
            FROM evidence e
            LEFT JOIN evidence_validations v ON v.evidence_id = e.id
            WHERE e.case_id = ?
            ORDER BY e.uploaded_at
            """,
            (session["case_id"],),
        ).fetchall()
        proposals = c.execute(
            "SELECT id, feature, original_value, proposed_value, evidence_id, status FROM proposals WHERE case_id = ?",
            (session["case_id"],),
        ).fetchall()
    return {
        "evidence": [
            {
                "id": r["id"],
                "target_feature": r["target_feature"],
                "doc_type": r["doc_type"],
                "extracted": json.loads(r["extracted_json"] or "{}").get("fields", {}),
                "extracted_value": r["extracted_value"],
                "uploaded_at": r["uploaded_at"],
                "overall": r["overall"],
                "summary": r["summary"],
                "checks": json.loads(r["checks_json"] or "[]"),
            }
            for r in rows
        ],
        "proposals": [dict(p) for p in proposals],
    }


@router.delete("/evidence/{evidence_id}")
def delete_evidence(evidence_id: str, session: dict = Depends(require_session)) -> dict:
    ok = evidence_pipeline.delete_evidence(session["case_id"], evidence_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"error": {"code": "not_found", "message": "No such evidence."}})
    return {"status": "deleted", "evidence_id": evidence_id}
