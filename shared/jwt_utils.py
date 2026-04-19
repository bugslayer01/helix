"""JWT signing/verification + webhook HMAC used across LenderCo and Recourse.

Two separate secrets:
- ``HELIX_JWT_SECRET`` — HS256 secret for handoff tokens LenderCo mints and Recourse verifies.
- ``HELIX_WEBHOOK_SECRET`` — HMAC-SHA256 secret for webhook body signatures.

Both default to development values if unset, so local demo works out of the box.
Production deployments must override via ``.env`` or the hosting platform's secret store.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from dataclasses import dataclass
from typing import Literal

import jwt

_DEV_JWT_SECRET = "dev-jwt-secret-change-me"
_DEV_WEBHOOK_SECRET = "dev-webhook-secret-change-me"
_ALG = "HS256"
_DEFAULT_TTL_HOURS = 24


def _jwt_secret() -> str:
    return os.environ.get("HELIX_JWT_SECRET", _DEV_JWT_SECRET)


def _webhook_secret() -> str:
    return os.environ.get("HELIX_WEBHOOK_SECRET", _DEV_WEBHOOK_SECRET)


@dataclass(frozen=True)
class HandoffClaims:
    iss: str
    sub: str
    case_id: str
    decision: Literal["approved", "denied"]
    issued_at: int
    exp: int
    jti: str


class HandoffError(Exception):
    """Raised when a handoff token cannot be verified."""


def sign_handoff(
    *,
    case_id: str,
    applicant_id: str,
    decision: Literal["approved", "denied"],
    issuer: str = "lenderco",
    ttl_hours: int | None = None,
) -> tuple[str, str]:
    """Return ``(token, jti)``. Caller stores ``jti`` in ``contest_handoffs`` table."""
    now = int(time.time())
    ttl = ttl_hours if ttl_hours is not None else int(os.environ.get("HELIX_JWT_TTL_HOURS", _DEFAULT_TTL_HOURS))
    jti = uuid.uuid4().hex
    payload = {
        "iss": issuer,
        "sub": applicant_id,
        "case_id": case_id,
        "decision": decision,
        "issued_at": now,
        "exp": now + ttl * 3600,
        "jti": jti,
    }
    token = jwt.encode(payload, _jwt_secret(), algorithm=_ALG)
    return token, jti


def verify_handoff(token: str) -> HandoffClaims:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_ALG])
    except jwt.ExpiredSignatureError as exc:
        raise HandoffError("handoff_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HandoffError("handoff_invalid") from exc
    try:
        return HandoffClaims(
            iss=str(payload["iss"]),
            sub=str(payload["sub"]),
            case_id=str(payload["case_id"]),
            decision=payload["decision"],
            issued_at=int(payload["issued_at"]),
            exp=int(payload["exp"]),
            jti=str(payload["jti"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise HandoffError("handoff_malformed") from exc


def sign_webhook_body(body: bytes) -> str:
    mac = hmac.new(_webhook_secret().encode(), body, hashlib.sha256)
    return mac.hexdigest()


def verify_webhook_body(body: bytes, signature: str) -> None:
    expected = sign_webhook_body(body)
    if not hmac.compare_digest(expected, signature):
        raise HandoffError("webhook_signature_invalid")


def hash_dob(dob_iso: str, case_salt: str) -> str:
    """Return the canonical DOB hash used on both sides for 2FA equality checks."""
    return "sha256:" + hashlib.sha256(f"{dob_iso}|{case_salt}".encode()).hexdigest()
