from __future__ import annotations

from fastapi import APIRouter

from services import audit_log

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{case_id}")
def get_audit(case_id: str) -> dict:
    return {"case_id": case_id, "entries": audit_log.list_for_case(case_id)}
