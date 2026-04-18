from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from seed_cases import SEED_CASES
from services import audit_log

router = APIRouter(prefix="/review", tags=["review"])


class ReviewRequest(BaseModel):
    case_id: str
    review_reason: str
    user_statement: str = Field(default="", max_length=2000)


# In-memory queue for demo purposes only.
_QUEUE: list[str] = []


@router.post("")
def request_review(req: ReviewRequest) -> dict:
    """Path 3 — human review. Does NOT re-run the classifier."""
    if req.case_id not in SEED_CASES:
        raise HTTPException(status_code=404, detail="Unknown case_id")
    if req.case_id not in _QUEUE:
        _QUEUE.append(req.case_id)
    position = _QUEUE.index(req.case_id) + 1

    entry = audit_log.append(
        case_id=req.case_id,
        action="human_review_requested",
        title="Queued for human review",
        subtitle=f"reason: {req.review_reason} · no model re-run",
        payload={
            "review_reason": req.review_reason,
            "statement_length": len(req.user_statement),
        },
        kind="success",
    )

    return {
        "case_id": req.case_id,
        "queue_position": position,
        "estimated_review_window": "72 hours",
        "audit_entry_id": entry["id"],
        "audit_hash": entry["hash"],
        "status": "queued_for_human_review",
    }
