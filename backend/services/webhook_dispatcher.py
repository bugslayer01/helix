"""Webhook dispatcher — sends the verdict back to LenderCo with retries + idempotency."""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Any

import httpx

from backend import db as _db
from backend.services import audit_log
from shared.jwt_utils import sign_webhook_body


def _lender_base() -> str:
    return os.environ.get("HELIX_LENDER_BASE_URL", "http://localhost:8001").rstrip("/")


def _max_attempts() -> int:
    return int(os.environ.get("HELIX_WEBHOOK_MAX_ATTEMPTS", 5))


def create_webhook(case_id: str, verdict: dict[str, Any]) -> str:
    webhook_id = "wh_" + uuid.uuid4().hex[:12]
    with _db.conn() as c:
        c.execute(
            """
            INSERT INTO verdict_webhooks (id, case_id, new_decision, new_prob_bad, new_features, delta_json, attempts)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                webhook_id,
                case_id,
                verdict["new_verdict"],
                verdict["new_prob_bad"],
                json.dumps(verdict["new_features"]),
                json.dumps(verdict["delta"]),
            ),
        )
    return webhook_id


def _body(case_id: str, verdict: dict[str, Any], audit_head: str | None, evidence_manifest: list[dict[str, Any]]) -> bytes:
    payload = {
        "case_id": case_id,
        "outcome": verdict["outcome"],
        "new_decision": {"verdict": verdict["new_verdict"], "prob_bad": verdict["new_prob_bad"]},
        "new_features": verdict["new_features"],
        "delta": verdict["delta"],
        "audit_chain_head": audit_head,
        "evidence_manifest": evidence_manifest,
        "model_version": verdict["model_version"],
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def _external_case_id(case_id: str) -> str | None:
    with _db.conn() as c:
        row = c.execute("SELECT external_case_id FROM contest_cases WHERE id = ?", (case_id,)).fetchone()
    return row["external_case_id"] if row else None


def _evidence_manifest(case_id: str) -> list[dict[str, Any]]:
    with _db.conn() as c:
        rows = c.execute(
            """
            SELECT e.id, e.sha256, e.doc_type, ev.overall
            FROM evidence e
            LEFT JOIN evidence_validations ev ON ev.evidence_id = e.id
            WHERE e.case_id = ?
            """,
            (case_id,),
        ).fetchall()
    return [{"id": r["id"], "sha256": r["sha256"], "doc_type": r["doc_type"], "overall": r["overall"]} for r in rows]


async def deliver(webhook_id: str) -> dict[str, Any]:
    with _db.conn() as c:
        wh = c.execute("SELECT * FROM verdict_webhooks WHERE id = ?", (webhook_id,)).fetchone()
        if not wh:
            return {"ok": False, "error": "webhook_not_found"}
        case_row = c.execute("SELECT * FROM contest_cases WHERE id = ?", (wh["case_id"],)).fetchone()
    if not case_row:
        return {"ok": False, "error": "case_not_found"}

    head = None
    rows = audit_log.list_for_case(wh["case_id"])
    if rows:
        head = rows[-1]["full_hash"]

    external_case = case_row["external_case_id"]
    verdict = {
        "outcome": "flipped" if case_row["status"] == "verdict_flipped" else "held",
        "new_verdict": wh["new_decision"],
        "new_prob_bad": wh["new_prob_bad"],
        "new_features": json.loads(wh["new_features"]),
        "delta": json.loads(wh["delta_json"]),
        "model_version": case_row["model_version"],
    }
    body = _body(external_case, verdict, head, _evidence_manifest(wh["case_id"]))
    sig = sign_webhook_body(body)
    headers = {
        "Authorization": f"Bearer {sig}",
        "Idempotency-Key": webhook_id,
        "Content-Type": "application/json",
    }

    audit_log.append(
        wh["case_id"],
        "webhook_dispatched",
        {"webhook_id": webhook_id, "target": f"{_lender_base()}/api/v1/recourse/verdicts"},
    )
    last_error: str | None = None
    for attempt in range(1, _max_attempts() + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{_lender_base()}/api/v1/recourse/verdicts", content=body, headers=headers)
            if 200 <= resp.status_code < 300:
                now = int(time.time())
                with _db.conn() as c:
                    c.execute(
                        "UPDATE verdict_webhooks SET delivered_at = ?, attempts = ?, last_error = NULL WHERE id = ?",
                        (now, attempt, webhook_id),
                    )
                    c.execute("UPDATE contest_cases SET closed_at = ?, status = CASE WHEN status IN ('verdict_held','verdict_flipped') THEN 'closed' ELSE status END WHERE id = ?", (now, wh["case_id"]))
                audit_log.append(wh["case_id"], "webhook_delivered", {"webhook_id": webhook_id, "attempt": attempt})
                return {"ok": True, "attempt": attempt, "audit_head": head}
            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:  # httpx and anything else
            last_error = f"{type(exc).__name__}: {exc}"
        await asyncio.sleep(min(2 ** attempt, 60))

    with _db.conn() as c:
        c.execute("UPDATE verdict_webhooks SET attempts = ?, last_error = ? WHERE id = ?", (_max_attempts(), last_error, webhook_id))
    audit_log.append(wh["case_id"], "webhook_failed", {"webhook_id": webhook_id, "last_error": last_error})
    return {"ok": False, "error": last_error}
