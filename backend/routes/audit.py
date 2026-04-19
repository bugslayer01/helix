from __future__ import annotations

from fastapi import APIRouter

from backend.services import audit_log

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/{case_id}")
def get_audit(case_id: str) -> dict:
    return {"case_id": case_id, "entries": audit_log.list_for_case(case_id)}


@router.get("/{case_id}/verify")
def verify_audit(case_id: str) -> dict:
    result = audit_log.verify(case_id)
    return {"case_id": case_id, **result}
