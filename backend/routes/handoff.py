"""Handoff routes: JWT preview, exchange + DOB 2FA, session boot."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from backend.services import handoff as handoff_svc
from shared.jwt_utils import HandoffError

router = APIRouter(prefix="/api/v1/contest", tags=["contest-handoff"])


class PreviewReq(BaseModel):
    token: str


class OpenReq(BaseModel):
    token: str
    dob: str


@router.post("/session/preview")
def preview(req: PreviewReq) -> dict:
    try:
        return handoff_svc.preview(req.token)
    except HandoffError as exc:
        raise HTTPException(status_code=401, detail={"error": {"code": str(exc), "message": "Cannot verify handoff token."}})


@router.post("/open")
def open_contest(req: OpenReq, response: Response) -> dict:
    try:
        result = handoff_svc.open_contest_session(token=req.token, dob=req.dob)
    except HandoffError as exc:
        status = 403 if str(exc) in {"dob_mismatch", "case_revoked"} else 401
        raise HTTPException(status_code=status, detail={"error": {"code": str(exc), "message": _humanize(str(exc))}})

    response.set_cookie(
        key="hx_session",
        value=result["session_id"],
        httponly=True,
        samesite="lax",
        max_age=24 * 3600,
    )
    return {
        "case_id": result["case_id"],
        "snapshot": result["snapshot"],
    }


def require_session(request: Request) -> dict:
    sid = request.cookies.get("hx_session")
    session = handoff_svc.load_session(sid) if sid else None
    if not session:
        raise HTTPException(status_code=401, detail={"error": {"code": "no_session", "message": "Session cookie missing or expired."}})
    if session["case_status"] == "revoked":
        raise HTTPException(status_code=403, detail={"error": {"code": "revoked", "message": "Case was revoked."}})
    return session


@router.get("/session")
def session_info(session: dict = Depends(require_session)) -> dict:
    case = handoff_svc.load_case(session["case_id"])
    if not case:
        raise HTTPException(status_code=404, detail={"error": {"code": "case_not_found", "message": "Case disappeared."}})
    return {
        "session_id": session["session_id"],
        "case_id": session["case_id"],
        "status": case["status"],
        "applicant_display": case["applicant_display"],
        "external_ref": case["external_ref"],
    }


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    sid = request.cookies.get("hx_session")
    handoff_svc.end_session(sid or "")
    response.delete_cookie("hx_session")
    return {"status": "logged_out"}


def _humanize(code: str) -> str:
    mapping = {
        "handoff_expired": "This contest link has expired. Request a fresh one from your lender.",
        "handoff_invalid": "This contest link is not valid.",
        "handoff_malformed": "This contest link is malformed.",
        "jti_already_consumed": "This contest link has already been used.",
        "dob_mismatch": "Date of birth does not match our records. Try again.",
        "case_revoked": "Your lender has revoked this contest.",
        "lender_error:401": "Your lender could not verify the contest link.",
        "lender_error:403": "Your lender has blocked this contest.",
        "lender_error:404": "Your lender cannot find the original application.",
    }
    return mapping.get(code, "We could not open this contest. Please try again later.")
