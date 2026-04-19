"""Contest case endpoints — snapshot, submit, outcome, revoke."""
from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request

from backend import db as _db
from backend.routes.handoff import require_session
from backend.services import handoff as handoff_svc
from backend.services import rerun, webhook_dispatcher
from backend.services.rerun import ModelDriftError
from shared.jwt_utils import HandoffError, verify_webhook_body

router = APIRouter(prefix="/api/v1/contest", tags=["contest"])


@router.get("/case")
def get_case(session: dict = Depends(require_session)) -> dict:
    case = handoff_svc.load_case(session["case_id"])
    if not case:
        raise HTTPException(status_code=404, detail={"error": {"code": "case_not_found", "message": "Case disappeared."}})
    return {
        "case_id": case["id"],
        "status": case["status"],
        "applicant_display": case["applicant_display"],
        "external_ref": case["external_ref"],
        "snapshot": {
            "features": json.loads(case["snapshot_features"]),
            "decision": json.loads(case["snapshot_decision"]),
            "shap": json.loads(case["snapshot_shap"]),
            "model_version": case["model_version"],
        },
    }


@router.post("/submit")
def submit_contest(background: BackgroundTasks, session: dict = Depends(require_session)) -> dict:
    case_id = session["case_id"]
    with _db.conn() as c:
        proposals = c.execute(
            "SELECT COUNT(*) AS n FROM proposals WHERE case_id = ? AND status = 'validated'",
            (case_id,),
        ).fetchone()
    if not proposals or proposals["n"] == 0:
        raise HTTPException(status_code=409, detail={"error": {"code": "no_proposals", "message": "Upload at least one piece of validated evidence first."}})

    try:
        verdict = rerun.rerun_for_case(case_id)
    except ModelDriftError as exc:
        raise HTTPException(status_code=409, detail={"error": {"code": "model_drift", "message": str(exc)}})
    webhook_id = webhook_dispatcher.create_webhook(case_id, verdict)
    background.add_task(webhook_dispatcher.deliver, webhook_id)

    return {
        "case_id": case_id,
        "outcome": verdict["outcome"],
        "new_decision": {"verdict": verdict["new_verdict"], "prob_bad": verdict["new_prob_bad"]},
        "new_features": verdict["new_features"],
        "new_shap": verdict["new_shap"],
        "delta": verdict["delta"],
        "webhook_id": webhook_id,
    }


@router.get("/outcome")
def outcome(session: dict = Depends(require_session)) -> dict:
    case = handoff_svc.load_case(session["case_id"])
    if not case:
        raise HTTPException(status_code=404, detail={"error": {"code": "case_not_found", "message": "Case disappeared."}})
    with _db.conn() as c:
        webhook = c.execute(
            "SELECT id, new_decision, new_prob_bad, new_features, delta_json, delivered_at, attempts, last_error FROM verdict_webhooks WHERE case_id = ? ORDER BY rowid DESC LIMIT 1",
            (session["case_id"],),
        ).fetchone()
    return {
        "status": case["status"],
        "snapshot_decision": json.loads(case["snapshot_decision"]),
        "webhook": (
            {
                "id": webhook["id"],
                "new_decision": {"verdict": webhook["new_decision"], "prob_bad": webhook["new_prob_bad"]},
                "new_features": json.loads(webhook["new_features"]),
                "delta": json.loads(webhook["delta_json"]),
                "delivered_at": webhook["delivered_at"],
                "attempts": webhook["attempts"],
                "last_error": webhook["last_error"],
            }
            if webhook
            else None
        ),
    }


# --- revoke endpoint (HMAC-authenticated, called by LenderCo) -------------

revoke_router = APIRouter(prefix="/api/v1/recourse", tags=["recourse"])


@revoke_router.post("/revoke")
async def revoke(request: Request, authorization: str | None = Header(default=None)) -> dict:
    body = await request.body()
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"error": {"code": "missing_hmac", "message": "HMAC required."}})
    sig = authorization.split(None, 1)[1].strip()
    try:
        verify_webhook_body(body, sig)
    except HandoffError as exc:
        raise HTTPException(status_code=401, detail={"error": {"code": str(exc), "message": "Signature invalid."}})
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail={"error": {"code": "bad_json", "message": "Body is not JSON."}})
    case_id = payload.get("case_id")
    if not case_id:
        raise HTTPException(status_code=400, detail={"error": {"code": "missing_case_id", "message": "case_id required."}})
    ok = handoff_svc.revoke(case_id)
    return {"status": "revoked" if ok else "not_found"}
