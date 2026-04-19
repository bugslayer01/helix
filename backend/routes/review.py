from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.routes.handoff import require_session
from backend.services import audit_log

router = APIRouter(prefix="/api/v1/contest", tags=["contest-review"])


class ReviewRequest(BaseModel):
    review_reason: str
    user_statement: str = Field(default="", max_length=2000)


_QUEUE: list[str] = []


@router.post("/request-review")
def request_review(req: ReviewRequest, session: dict = Depends(require_session)) -> dict:
    """Path 3 — queue for human review. No model re-run."""
    case_id = session["case_id"]
    if case_id not in _QUEUE:
        _QUEUE.append(case_id)
    position = _QUEUE.index(case_id) + 1

    entry = audit_log.append(
        case_id=case_id,
        action="review_requested",
        payload={"review_reason": req.review_reason, "statement_length": len(req.user_statement)},
        title="Queued for human review",
        subtitle=f"reason: {req.review_reason} · no model re-run",
        kind="success",
    )

    return {
        "case_id": case_id,
        "queue_position": position,
        "estimated_review_window": "72 hours",
        "audit_hash": entry["hash"],
        "status": "queued_for_human_review",
    }
