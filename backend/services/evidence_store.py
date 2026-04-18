"""SQLite persistence for the propose/validate/apply contest flow.

Shares the same `audit.db` file as the audit log so a single DB ships the demo.
All writes go through a module-level lock; SQLite's own locking is fine for
reads.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "audit.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pending_contests (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    contest_path TEXT NOT NULL,
    reason_category TEXT NOT NULL,
    user_context TEXT,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pending_case ON pending_contests(case_id, created_at);

CREATE TABLE IF NOT EXISTS pending_proposals (
    id TEXT PRIMARY KEY,
    contest_id TEXT NOT NULL,
    feature TEXT NOT NULL,
    form_key TEXT NOT NULL,
    policy TEXT NOT NULL,
    proposed_value REAL,
    evidence_type TEXT,
    evidence_filename TEXT,
    evidence_hash TEXT,
    status TEXT NOT NULL,
    resolved_value REAL,
    validation_note TEXT,
    FOREIGN KEY(contest_id) REFERENCES pending_contests(id)
);
CREATE INDEX IF NOT EXISTS idx_proposal_contest ON pending_proposals(contest_id);
"""

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, _conn() as c:
        c.executescript(_SCHEMA)


def create_contest(
    case_id: str,
    contest_path: str,
    reason_category: str,
    user_context: str | None,
    proposals: list[dict[str, Any]],
) -> dict[str, Any]:
    contest_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    proposal_rows: list[dict[str, Any]] = []
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO pending_contests (id, case_id, contest_path, reason_category, user_context, created_at, status) VALUES (?,?,?,?,?,?,?)",
            (contest_id, case_id, contest_path, reason_category, user_context, created_at, "validating"),
        )
        for p in proposals:
            pid = str(uuid.uuid4())
            proposed = p.get("proposed_value")
            c.execute(
                "INSERT INTO pending_proposals (id, contest_id, feature, form_key, policy, proposed_value, evidence_type, evidence_filename, evidence_hash, status, resolved_value, validation_note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    pid,
                    contest_id,
                    p["feature"],
                    p["form_key"],
                    p["policy"],
                    float(proposed) if proposed is not None else None,
                    p.get("evidence_type"),
                    p.get("evidence_filename"),
                    p.get("evidence_hash"),
                    "validating",
                    None,
                    None,
                ),
            )
            proposal_rows.append(
                {
                    "id": pid,
                    "feature": p["feature"],
                    "form_key": p["form_key"],
                    "policy": p["policy"],
                    "proposed_value": proposed,
                    "evidence_type": p.get("evidence_type"),
                    "evidence_filename": p.get("evidence_filename"),
                    "evidence_hash": p.get("evidence_hash"),
                    "status": "validating",
                }
            )
    return {
        "id": contest_id,
        "case_id": case_id,
        "contest_path": contest_path,
        "reason_category": reason_category,
        "user_context": user_context,
        "created_at": created_at,
        "status": "validating",
        "proposals": proposal_rows,
    }


def get_contest(contest_id: str) -> dict[str, Any] | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM pending_contests WHERE id = ?", (contest_id,)
        ).fetchone()
        if row is None:
            return None
        proposals = c.execute(
            "SELECT * FROM pending_proposals WHERE contest_id = ? ORDER BY feature ASC",
            (contest_id,),
        ).fetchall()
    return {
        "id": row["id"],
        "case_id": row["case_id"],
        "contest_path": row["contest_path"],
        "reason_category": row["reason_category"],
        "user_context": row["user_context"],
        "created_at": row["created_at"],
        "status": row["status"],
        "proposals": [_proposal_dict(p) for p in proposals],
    }


def _proposal_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "contest_id": row["contest_id"],
        "feature": row["feature"],
        "form_key": row["form_key"],
        "policy": row["policy"],
        "proposed_value": row["proposed_value"],
        "evidence_type": row["evidence_type"],
        "evidence_filename": row["evidence_filename"],
        "evidence_hash": row["evidence_hash"],
        "status": row["status"],
        "resolved_value": row["resolved_value"],
        "validation_note": row["validation_note"],
    }


def update_proposal(
    proposal_id: str,
    *,
    status: str,
    resolved_value: float | None,
    validation_note: str | None,
) -> None:
    with _lock, _conn() as c:
        c.execute(
            "UPDATE pending_proposals SET status = ?, resolved_value = ?, validation_note = ? WHERE id = ?",
            (status, resolved_value, validation_note, proposal_id),
        )


def set_contest_status(contest_id: str, status: str) -> None:
    with _lock, _conn() as c:
        c.execute(
            "UPDATE pending_contests SET status = ? WHERE id = ?",
            (status, contest_id),
        )


def compute_aggregate_status(proposals: list[dict[str, Any]]) -> str:
    statuses = {p["status"] for p in proposals}
    if "validating" in statuses:
        return "validating"
    if statuses == {"rejected"}:
        return "rejected"
    if statuses == {"validated"} or statuses == {"validated", "applied"}:
        return "validated"
    if "validated" in statuses and "rejected" in statuses:
        return "partially_rejected"
    return "validating"
