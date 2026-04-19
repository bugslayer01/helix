"""SHA-256-chained audit log for Recourse contest cases.

Each row's ``hash`` is ``sha256(prev_hash | case_id | ts | action | canonical_payload)``.
A break anywhere in the chain is detectable by re-running :func:`verify`.

The schema lives in :mod:`backend.db` together with every other Recourse table
so the audit trail is part of the same WAL SQLite file as the case data it
audits. This means ``make reset`` wipes everything atomically.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from backend import db as _db

GENESIS = "0" * 64


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))


def _tail(conn, case_id: str) -> str:
    row = conn.execute(
        "SELECT hash FROM audit_log WHERE case_id = ? ORDER BY id DESC LIMIT 1",
        (case_id,),
    ).fetchone()
    return row["hash"] if row else GENESIS


def _compute(prev_hash: str, case_id: str, ts: int, action: str, payload_json: str) -> str:
    body = f"{prev_hash}|{case_id}|{ts}|{action}|{payload_json}"
    return hashlib.sha256(body.encode()).hexdigest()


def init_db() -> None:
    _db.init_db()


def append(
    case_id: str,
    action: str,
    payload: dict[str, Any] | None = None,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    kind: str = "info",
) -> dict[str, Any]:
    """Append a chained audit row and return the canonical record.

    ``title``/``subtitle``/``kind`` are folded into ``payload`` under a ``_display``
    key so older callers keep working without a second table column.
    """
    merged = dict(payload or {})
    display: dict[str, Any] = {}
    if title:
        display["title"] = title
    if subtitle:
        display["subtitle"] = subtitle
    if kind and kind != "info":
        display["kind"] = kind
    if display:
        merged["_display"] = display

    ts = int(time.time())
    body = _canonical(merged)
    with _db.conn() as c:
        prev_hash = _tail(c, case_id)
        h = _compute(prev_hash, case_id, ts, action, body)
        c.execute(
            "INSERT INTO audit_log (case_id, action, payload_json, prev_hash, hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (case_id, action, body, prev_hash, h, ts),
        )
    return {
        "case_id": case_id,
        "action": action,
        "payload": merged,
        "prev_hash": prev_hash,
        "hash": h,
        "created_at": ts,
    }


def list_for_case(case_id: str) -> list[dict[str, Any]]:
    with _db.conn() as c:
        rows = c.execute(
            "SELECT id, action, payload_json, prev_hash, hash, created_at FROM audit_log WHERE case_id = ? ORDER BY id",
            (case_id,),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        payload = json.loads(r["payload_json"] or "{}")
        display = payload.pop("_display", {}) if isinstance(payload, dict) else {}
        out.append(
            {
                "id": r["id"],
                "case_id": case_id,
                "action": r["action"],
                "payload": payload,
                "title": display.get("title"),
                "subtitle": display.get("subtitle"),
                "kind": display.get("kind", "info"),
                "hash": f"0x{r['hash'][:12]}",
                "full_hash": r["hash"],
                "prev_hash": r["prev_hash"],
                "created_at": r["created_at"],
            }
        )
    return out


def verify(case_id: str) -> dict[str, Any]:
    with _db.conn() as c:
        rows = c.execute(
            "SELECT id, action, payload_json, prev_hash, hash, created_at FROM audit_log WHERE case_id = ? ORDER BY id",
            (case_id,),
        ).fetchall()
    if not rows:
        return {"ok": True, "rows": 0, "head": None}
    prev = GENESIS
    for row in rows:
        expected = _compute(prev, case_id, row["created_at"], row["action"], row["payload_json"])
        if expected != row["hash"] or row["prev_hash"] != prev:
            return {"ok": False, "broken_at_row": row["id"], "rows": len(rows)}
        prev = row["hash"]
    return {"ok": True, "rows": len(rows), "head": prev}
