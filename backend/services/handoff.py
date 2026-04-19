"""Session + JTI management for Recourse contest handoffs."""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from typing import Any

import httpx

from backend import db as _db
from backend.services import audit_log
from shared.jwt_utils import HandoffClaims, HandoffError, verify_handoff

_CASE_SALT = "helix-demo-salt"  # must match LenderCo


def _dob_hash(dob_iso: str) -> str:
    return "sha256:" + hashlib.sha256(f"{dob_iso}|{_CASE_SALT}".encode()).hexdigest()


def _lender_base() -> str:
    return os.environ.get("HELIX_LENDER_BASE_URL", "http://localhost:8001").rstrip("/")


def _session_ttl() -> int:
    return int(os.environ.get("HELIX_SESSION_TTL_HOURS", 24)) * 3600


def preview(token: str) -> dict[str, Any]:
    """Lightweight JWT verify — used by the handoff landing page before DOB entry."""
    claims = verify_handoff(token)  # raises HandoffError
    return {
        "case_id": claims.case_id,
        "applicant_id": claims.sub,
        "issuer": claims.iss,
        "decision": claims.decision,
        "expires_at": claims.exp,
    }


def fetch_case_from_lender(claims: HandoffClaims, token: str) -> dict[str, Any]:
    url = f"{_lender_base()}/api/v1/cases/{claims.case_id}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers={"Authorization": f"Bearer {token}"})
    if resp.status_code >= 400:
        raise HandoffError(f"lender_error:{resp.status_code}")
    return resp.json()


def open_contest_session(*, token: str, dob: str) -> dict[str, Any]:
    """Exchange the handoff JWT + DOB for a session cookie.

    Steps:
    1. Verify JWT + expiry + jti not consumed (single-use within Recourse).
    2. Fetch case snapshot from LenderCo.
    3. Verify dob hash matches what LenderCo says.
    4. Create or reuse a ``contest_cases`` row, issue a session, mark jti consumed.
    """
    try:
        claims = verify_handoff(token)
    except HandoffError as exc:
        raise HandoffError(str(exc)) from exc

    now = int(time.time())
    if claims.exp < now:
        raise HandoffError("handoff_expired")

    snapshot = fetch_case_from_lender(claims, token)

    if _dob_hash(dob) != snapshot["applicant"]["dob_hash"]:
        raise HandoffError("dob_mismatch")

    case_id = "rc_" + uuid.uuid4().hex[:12]
    session_id = "s_" + uuid.uuid4().hex[:24]

    with _db.conn() as c:
        existing = c.execute(
            "SELECT id, status FROM contest_cases WHERE customer_id = ? AND external_case_id = ?",
            (claims.iss, claims.case_id),
        ).fetchone()
        if existing:
            case_id = existing["id"]
            if existing["status"] == "revoked":
                raise HandoffError("case_revoked")
        else:
            c.execute(
                """
                INSERT INTO contest_cases (
                    id, customer_id, external_case_id, external_ref,
                    applicant_display, applicant_dob_hash,
                    snapshot_features, snapshot_decision, snapshot_shap,
                    model_version, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
                """,
                (
                    case_id,
                    claims.iss,
                    claims.case_id,
                    snapshot.get("external_ref", claims.case_id),
                    snapshot["applicant"]["display_name"],
                    snapshot["applicant"]["dob_hash"],
                    json.dumps(snapshot["features"]),
                    json.dumps(snapshot["decision"]),
                    json.dumps(snapshot["shap"]),
                    snapshot["model_version"],
                    now,
                ),
            )
        # single-use jti (within Recourse — user can hit DOB wrong once and retry
        # because we insert only after snapshot + DOB succeeded).
        already = c.execute("SELECT 1 FROM used_jti WHERE jti = ?", (claims.jti,)).fetchone()
        if already:
            raise HandoffError("jti_already_consumed")
        c.execute("INSERT INTO used_jti (jti, consumed_at) VALUES (?, ?)", (claims.jti, now))
        c.execute(
            "INSERT INTO sessions (id, case_id, jti, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, case_id, claims.jti, now, now + _session_ttl()),
        )

    audit_log.append(
        case_id,
        "case_opened",
        {
            "issuer": claims.iss,
            "external_case_id": claims.case_id,
            "applicant_display": snapshot["applicant"]["display_name"],
            "model_version": snapshot["model_version"],
            "snapshot_decision": snapshot["decision"],
        },
        title="Contest opened",
        subtitle=f"JWT verified · DOB matched · session issued",
    )

    return {
        "session_id": session_id,
        "case_id": case_id,
        "snapshot": snapshot,
    }


def load_session(session_id: str) -> dict[str, Any] | None:
    if not session_id:
        return None
    now = int(time.time())
    with _db.conn() as c:
        row = c.execute(
            "SELECT s.*, cc.status AS case_status, cc.id AS case_id FROM sessions s JOIN contest_cases cc ON cc.id = s.case_id WHERE s.id = ?",
            (session_id,),
        ).fetchone()
    if not row or row["expires_at"] < now:
        return None
    return {
        "session_id": row["id"],
        "case_id": row["case_id"],
        "case_status": row["case_status"],
        "jti": row["jti"],
        "expires_at": row["expires_at"],
    }


def load_case(case_id: str) -> dict[str, Any] | None:
    with _db.conn() as c:
        row = c.execute("SELECT * FROM contest_cases WHERE id = ?", (case_id,)).fetchone()
    if not row:
        return None
    return dict(row)


def revoke(external_case_id: str, customer_id: str = "lenderco", reason: str | None = None) -> bool:
    now = int(time.time())
    with _db.conn() as c:
        row = c.execute(
            "SELECT id FROM contest_cases WHERE customer_id = ? AND external_case_id = ?",
            (customer_id, external_case_id),
        ).fetchone()
        if not row:
            return False
        c.execute(
            "UPDATE contest_cases SET status = 'revoked', closed_at = ? WHERE id = ?",
            (now, row["id"]),
        )
    audit_log.append(
        row["id"],
        "case_revoked",
        {"reason": reason, "customer_id": customer_id, "external_case_id": external_case_id},
        title="Case revoked",
        subtitle=f"reason: {reason or 'unspecified'}",
    )
    return True


def end_session(session_id: str) -> bool:
    """End a contest session (logout)."""
    if not session_id:
        return False
    with _db.conn() as c:
        row = c.execute("SELECT case_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return False
        c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    audit_log.append(
        row["case_id"],
        "session_closed",
        {"session_id": session_id},
        title="Session ended",
        subtitle="applicant signed out",
    )
    return True
