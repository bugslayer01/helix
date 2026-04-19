"""Recourse → LenderCo webhook receivers."""
from __future__ import annotations

import json
import time
import uuid

from fastapi import APIRouter, Header, HTTPException, Request

from customer_portal.backend import db
from shared.jwt_utils import HandoffError, verify_webhook_body

router = APIRouter(prefix="/api/v1/recourse", tags=["recourse-webhooks"])


@router.post("/verdicts")
async def receive_verdict(request: Request, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> dict:
    body = await request.body()
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"error": {"code": "missing_hmac", "message": "Authorization Bearer (HMAC) required."}})
    sig = authorization.split(None, 1)[1].strip()
    try:
        verify_webhook_body(body, sig)
    except HandoffError as exc:
        raise HTTPException(status_code=401, detail={"error": {"code": str(exc), "message": "Webhook signature invalid."}})
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail={"error": {"code": "malformed_body", "message": "Not JSON."}})

    case_id = payload.get("case_id")
    new_decision = payload.get("new_decision") or {}
    new_features = payload.get("new_features") or {}
    delta = payload.get("delta") or []
    model_version = payload.get("model_version")
    if not case_id or not new_decision.get("verdict"):
        raise HTTPException(status_code=400, detail={"error": {"code": "missing_fields", "message": "case_id and new_decision required."}})

    with db.conn() as c:
        app_row = c.execute("SELECT * FROM applications WHERE id = ?", (case_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail={"error": {"code": "case_not_found", "message": "Unknown case."}})
        scored = c.execute("SELECT model_version FROM scored_features WHERE application_id = ?", (case_id,)).fetchone()
        if scored and model_version and scored["model_version"] != model_version:
            raise HTTPException(
                status_code=409,
                detail={"error": {"code": "model_version_mismatch", "message": f"Recourse ran {model_version}, LenderCo has {scored['model_version']}."}},
            )

        # Idempotency: if we already have a decision with this Idempotency-Key note, skip.
        if idempotency_key:
            hit = c.execute(
                "SELECT id FROM decisions WHERE application_id = ? AND shap_json LIKE ?",
                (case_id, f"%\"idempotency_key\": \"{idempotency_key}\"%"),
            ).fetchone()
            if hit:
                return {"status": "ok", "decision_id": hit["id"], "replayed": True}

        now = int(time.time())
        decision_id = "dec_" + uuid.uuid4().hex[:12]
        # We store the verdict WITH its delta context so operator UI can render it.
        shap_blob = json.dumps({
            "new_features": new_features,
            "delta": delta,
            "evidence_manifest": payload.get("evidence_manifest", []),
            "audit_chain_head": payload.get("audit_chain_head"),
            "idempotency_key": idempotency_key,
        })
        c.execute(
            "INSERT INTO decisions (id, application_id, verdict, prob_bad, shap_json, top_reasons, source, decided_at) VALUES (?, ?, ?, ?, ?, ?, 'recourse_webhook', ?)",
            (decision_id, case_id, new_decision["verdict"], new_decision.get("prob_bad", 0), shap_blob, json.dumps([]), now),
        )
        c.execute("UPDATE applications SET status = 'closed', decided_at = ? WHERE id = ?", (now, case_id))

    return {"status": "ok", "decision_id": decision_id, "replayed": False}
