"""LenderCo applicant-facing endpoints: submit app, upload docs, poll decision, request contest link."""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from customer_portal.backend import db
from customer_portal.backend.services import intake, scorer
from shared.jwt_utils import sign_handoff

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])


_UPLOAD_DIR = Path(os.environ.get("HELIX_LENDER_UPLOADS", "customer_portal/backend/uploads"))


class StartApplication(BaseModel):
    full_name: str = Field(min_length=1, max_length=80)
    dob: str
    email: str
    phone: str | None = None
    amount: int = Field(gt=0)
    purpose: str | None = None


@router.post("")
def start_application(req: StartApplication) -> dict:
    now = int(time.time())
    applicant_id = "APP-" + uuid.uuid4().hex[:8].upper()
    application_id = "LN-2026-" + uuid.uuid4().hex[:4].upper()
    with db.conn() as c:
        c.execute(
            "INSERT INTO applicants (id, full_name, dob, email, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (applicant_id, req.full_name.strip(), req.dob, req.email.strip(), (req.phone or "").strip() or None, now),
        )
        c.execute(
            "INSERT INTO applications (id, applicant_id, amount, purpose, status, submitted_at) VALUES (?, ?, ?, ?, 'intake', ?)",
            (application_id, applicant_id, req.amount, req.purpose, now),
        )
    return {
        "application_id": application_id,
        "applicant_id": applicant_id,
        "status": "intake",
    }


@router.post("/{app_id}/documents")
async def upload_document(app_id: str, doc_type: str = Form(...), file: UploadFile = File(...)) -> dict:
    with db.conn() as c:
        app_row = c.execute("SELECT status FROM applications WHERE id = ?", (app_id,)).fetchone()
    if not app_row:
        raise HTTPException(status_code=404, detail={"error": {"code": "application_not_found", "message": "Unknown application."}})
    if app_row["status"] not in ("intake", "under_review"):
        raise HTTPException(status_code=409, detail={"error": {"code": "locked", "message": "Application is past intake."}})

    blob = await file.read()
    if not blob:
        raise HTTPException(status_code=400, detail={"error": {"code": "empty_upload", "message": "Empty file."}})
    sha = hashlib.sha256(blob).hexdigest()
    doc_id = "doc_" + uuid.uuid4().hex[:12]
    target_dir = _UPLOAD_DIR / app_id
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "upload.bin").name
    ext = Path(safe_name).suffix or ".bin"
    stored_path = target_dir / f"{doc_id}{ext}"
    stored_path.write_bytes(blob)

    # Run extraction right away so downstream submit is instant.
    try:
        extracted = intake.extract_doc(stored_path, doc_type)
    except Exception as exc:  # extractor failure should not kill upload
        extracted = {"doc_type": doc_type, "extracted": {}, "text_layer": "", "source": "error", "confidence": 0.0, "error": str(exc)}

    now = int(time.time())
    with db.conn() as c:
        c.execute(
            "INSERT INTO intake_documents (id, application_id, doc_type, original_name, stored_path, sha256, extracted_json, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (doc_id, app_id, doc_type, safe_name, str(stored_path), sha, json.dumps(extracted), now),
        )
    return {
        "document_id": doc_id,
        "doc_type": doc_type,
        "sha256": sha,
        "extracted": extracted.get("extracted", {}),
        "source": extracted.get("source"),
        "confidence": extracted.get("confidence"),
    }


@router.post("/{app_id}/submit")
def submit(app_id: str) -> dict:
    with db.conn() as c:
        app_row = c.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail={"error": {"code": "application_not_found", "message": "Unknown application."}})
        if app_row["status"] != "intake":
            raise HTTPException(status_code=409, detail={"error": {"code": "already_submitted", "message": "Already submitted."}})
        applicant = c.execute("SELECT * FROM applicants WHERE id = ?", (app_row["applicant_id"],)).fetchone()
        doc_rows = c.execute("SELECT doc_type, extracted_json FROM intake_documents WHERE application_id = ?", (app_id,)).fetchall()

    doc_records = []
    for d in doc_rows:
        try:
            doc_records.append(json.loads(d["extracted_json"] or "{}"))
        except json.JSONDecodeError:
            continue

    features = intake.assemble_features(
        domain="loans",
        applicant_dob=applicant["dob"],
        doc_records=doc_records,
    )
    scored = scorer.score("loans", features)

    now = int(time.time())
    decision_id = "dec_" + uuid.uuid4().hex[:12]
    with db.conn() as c:
        c.execute(
            "INSERT INTO scored_features (application_id, feature_vector, model_version, scored_at) VALUES (?, ?, ?, ?)",
            (app_id, json.dumps(features), scored["model_version"], now),
        )
        c.execute(
            "INSERT INTO decisions (id, application_id, verdict, prob_bad, shap_json, top_reasons, source, decided_at) VALUES (?, ?, ?, ?, ?, ?, 'initial', ?)",
            (decision_id, app_id, scored["verdict"], scored["prob_bad"], json.dumps(scored["shap"]), json.dumps(scored["top_reasons"]), now),
        )
        c.execute("UPDATE applications SET status = 'decided', decided_at = ? WHERE id = ?", (now, app_id))

    return {
        "application_id": app_id,
        "decision": {
            "id": decision_id,
            "verdict": scored["verdict"],
            "prob_bad": scored["prob_bad"],
            "top_reasons": scored["top_reasons"],
            "shap": scored["shap"],
            "model_version": scored["model_version"],
        },
        "features": features,
    }


@router.get("/{app_id}")
def get_application(app_id: str) -> dict:
    with db.conn() as c:
        app_row = c.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail={"error": {"code": "application_not_found", "message": "Unknown application."}})
        applicant = c.execute("SELECT * FROM applicants WHERE id = ?", (app_row["applicant_id"],)).fetchone()
        decision = c.execute(
            "SELECT * FROM decisions WHERE application_id = ? ORDER BY decided_at DESC LIMIT 1",
            (app_id,),
        ).fetchone()
        docs = c.execute(
            "SELECT id, doc_type, original_name, uploaded_at FROM intake_documents WHERE application_id = ? ORDER BY uploaded_at",
            (app_id,),
        ).fetchall()
    return {
        "application": {
            "id": app_row["id"],
            "amount": app_row["amount"],
            "purpose": app_row["purpose"],
            "status": app_row["status"],
            "submitted_at": app_row["submitted_at"],
            "decided_at": app_row["decided_at"],
        },
        "applicant": {
            "full_name": applicant["full_name"],
            "dob": applicant["dob"],
            "email": applicant["email"],
        },
        "documents": [dict(d) for d in docs],
        "decision": (
            {
                "id": decision["id"],
                "verdict": decision["verdict"],
                "prob_bad": decision["prob_bad"],
                "top_reasons": json.loads(decision["top_reasons"] or "[]"),
                "shap": json.loads(decision["shap_json"] or "[]"),
                "source": decision["source"],
                "decided_at": decision["decided_at"],
            }
            if decision
            else None
        ),
    }


@router.post("/{app_id}/request-contest-link")
def request_contest_link(app_id: str) -> dict:
    with db.conn() as c:
        app_row = c.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail={"error": {"code": "application_not_found", "message": "Unknown application."}})
        decision = c.execute(
            "SELECT verdict FROM decisions WHERE application_id = ? ORDER BY decided_at DESC LIMIT 1",
            (app_id,),
        ).fetchone()
    if not decision or decision["verdict"] != "denied":
        raise HTTPException(status_code=409, detail={"error": {"code": "not_contestable", "message": "Only denied applications can be contested."}})

    token, jti = sign_handoff(
        case_id=app_row["id"],
        applicant_id=app_row["applicant_id"],
        decision="denied",
    )
    now = int(time.time())
    with db.conn() as c:
        c.execute(
            "INSERT INTO contest_handoffs (jti, application_id, issued_at, expires_at) VALUES (?, ?, ?, ?)",
            (jti, app_id, now, now + 86400),
        )
        c.execute("UPDATE applications SET status = 'in_contest' WHERE id = ?", (app_id,))

    recourse_base = os.environ.get("HELIX_RECOURSE_PORTAL_URL", "http://localhost:5173")
    return {
        "contest_url": f"{recourse_base}/?t={token}",
        "jti": jti,
        "expires_in_hours": 24,
    }
