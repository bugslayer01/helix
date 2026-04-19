"""Hiring endpoints: create posting, submit candidate, view decision, mint contest link."""
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
from customer_portal.backend.services import hiring_intake
from shared.jwt_utils import sign_handoff

router = APIRouter(prefix="/api/v1/hiring", tags=["hiring"])

_UPLOAD_DIR = Path(os.environ.get("HELIX_LENDER_UPLOADS", "customer_portal/backend/uploads"))


class CreatePosting(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    jd_text: str = Field(min_length=20, max_length=20000)


@router.post("/postings")
def create_posting(req: CreatePosting) -> dict:
    posting_id = "JOB-2026-" + uuid.uuid4().hex[:6].upper()
    now = int(time.time())
    with db.conn() as c:
        c.execute(
            "INSERT INTO job_postings (id, title, jd_text, created_at) VALUES (?, ?, ?, ?)",
            (posting_id, req.title.strip(), req.jd_text.strip(), now),
        )
    return {"posting_id": posting_id, "title": req.title}


@router.get("/postings")
def list_postings() -> dict:
    with db.conn() as c:
        rows = c.execute(
            "SELECT id, title, jd_text, created_at FROM job_postings ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    return {"postings": [dict(r) for r in rows]}


@router.post("/postings/{posting_id}/candidates")
async def submit_candidate(
    posting_id: str,
    full_name: str = Form(...),
    dob: str = Form(...),
    email: str = Form(...),
    resume: UploadFile = File(...),
) -> dict:
    with db.conn() as c:
        posting = c.execute("SELECT * FROM job_postings WHERE id = ?", (posting_id,)).fetchone()
    if not posting:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "posting_not_found", "message": "Unknown job posting."}},
        )

    blob = await resume.read()
    if not blob:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "empty_resume", "message": "Empty resume file."}},
        )

    applicant_id = "CAN-" + uuid.uuid4().hex[:8].upper()
    application_id = "HR-2026-" + uuid.uuid4().hex[:4].upper()
    target_dir = _UPLOAD_DIR / application_id
    target_dir.mkdir(parents=True, exist_ok=True)
    resume_path = target_dir / "resume.pdf"
    resume_path.write_bytes(blob)
    resume_text = hiring_intake.extract_resume_text(resume_path)

    scored = hiring_intake.score_application(posting["jd_text"], resume_text)
    now = int(time.time())
    decision_id = "dec_" + uuid.uuid4().hex[:12]

    with db.conn() as c:
        c.execute(
            "INSERT INTO applicants (id, full_name, dob, email, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (applicant_id, full_name.strip(), dob, email.strip(), None, now),
        )
        c.execute(
            "INSERT INTO hiring_applications (id, applicant_id, posting_id, resume_text, resume_path, status, submitted_at, decided_at) VALUES (?, ?, ?, ?, ?, 'decided', ?, ?)",
            (application_id, applicant_id, posting_id, resume_text, str(resume_path), now, now),
        )
        c.execute(
            "INSERT INTO applications (id, applicant_id, amount, purpose, status, submitted_at, decided_at) VALUES (?, ?, 0, ?, 'decided', ?, ?)",
            (application_id, applicant_id, f"hiring · {posting['title']}", now, now),
        )
        c.execute(
            "INSERT INTO scored_features (application_id, feature_vector, model_version, scored_at) VALUES (?, ?, ?, ?)",
            (application_id, json.dumps({"jd_text": posting["jd_text"], "resume_text_sha": hashlib.sha256(resume_text.encode()).hexdigest()}), scored["model_version"], now),
        )
        c.execute(
            "INSERT INTO decisions (id, application_id, verdict, prob_bad, shap_json, top_reasons, source, decided_at) VALUES (?, ?, ?, ?, ?, ?, 'initial', ?)",
            (decision_id, application_id, scored["verdict"], scored["prob_bad"], json.dumps(scored["shap"]), json.dumps(scored["top_reasons"]), now),
        )

    return {
        "application_id": application_id,
        "applicant_id": applicant_id,
        "posting_id": posting_id,
        "decision": {
            "id": decision_id,
            "verdict": scored["verdict"],
            "prob_bad": scored["prob_bad"],
            "confidence": scored["confidence"],
            "top_reasons": scored["top_reasons"],
            "shap": scored["shap"],
            "model_version": scored["model_version"],
        },
    }


@router.get("/applications/{app_id}")
def get_hiring_application(app_id: str) -> dict:
    with db.conn() as c:
        app_row = c.execute("SELECT * FROM hiring_applications WHERE id = ?", (app_id,)).fetchone()
        if not app_row:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "not_found", "message": "Unknown hiring application."}},
            )
        applicant = c.execute("SELECT * FROM applicants WHERE id = ?", (app_row["applicant_id"],)).fetchone()
        decision = c.execute(
            "SELECT * FROM decisions WHERE application_id = ? ORDER BY decided_at DESC LIMIT 1",
            (app_id,),
        ).fetchone()
        posting = c.execute("SELECT id, title, jd_text FROM job_postings WHERE id = ?", (app_row["posting_id"],)).fetchone()
    return {
        "application": dict(app_row),
        "applicant": dict(applicant),
        "posting": dict(posting),
        "decision": (
            {
                "id": decision["id"],
                "verdict": decision["verdict"],
                "prob_bad": decision["prob_bad"],
                "confidence": round(1.0 - float(decision["prob_bad"]), 4),
                "top_reasons": json.loads(decision["top_reasons"] or "[]"),
                "shap": json.loads(decision["shap_json"] or "[]"),
                "source": decision["source"],
                "decided_at": decision["decided_at"],
            }
            if decision
            else None
        ),
    }


@router.post("/applications/{app_id}/request-contest-link")
def hiring_contest_link(app_id: str) -> dict:
    with db.conn() as c:
        app_row = c.execute("SELECT * FROM hiring_applications WHERE id = ?", (app_id,)).fetchone()
    if not app_row:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "Unknown hiring application."}},
        )

    with db.conn() as c:
        decision = c.execute(
            "SELECT verdict FROM decisions WHERE application_id = ? ORDER BY decided_at DESC LIMIT 1",
            (app_id,),
        ).fetchone()
    if not decision or decision["verdict"] != "denied":
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "not_contestable", "message": "Only denied applications can be contested."}},
        )

    token, jti = sign_handoff(case_id=app_id, applicant_id=app_row["applicant_id"], decision="denied")
    now = int(time.time())
    with db.conn() as c:
        c.execute(
            "INSERT INTO contest_handoffs (jti, application_id, issued_at, expires_at) VALUES (?, ?, ?, ?)",
            (jti, app_id, now, now + 86400),
        )
        c.execute("UPDATE hiring_applications SET status = 'in_contest' WHERE id = ?", (app_id,))
        c.execute("UPDATE applications SET status = 'in_contest' WHERE id = ?", (app_id,))

    recourse_base = os.environ.get("HELIX_RECOURSE_PORTAL_URL", "http://localhost:5173")
    return {"contest_url": f"{recourse_base}/?t={token}", "jti": jti, "expires_in_hours": 24}
