"""SQLite-backed tamper-evident audit log.

Each entry's hash covers the previous entry's hash + a canonical JSON
serialization of the new entry, giving a forward-chained integrity trail.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "audit.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_entries (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL,
    payload TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'info'
);
CREATE INDEX IF NOT EXISTS idx_case_ts ON audit_entries(case_id, timestamp);
"""

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _conn() as c:
        c.executescript(_SCHEMA)


def _last_hash(c: sqlite3.Connection, case_id: str) -> str:
    row = c.execute(
        "SELECT hash FROM audit_entries WHERE case_id = ? ORDER BY timestamp DESC, id DESC LIMIT 1",
        (case_id,),
    ).fetchone()
    return row[0] if row else "genesis"


def append(
    case_id: str,
    action: str,
    title: str,
    subtitle: str,
    payload: dict[str, Any] | None = None,
    kind: str = "info",
) -> dict[str, Any]:
    entry_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()
    payload_str = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
    with _lock, _conn() as c:
        prev = _last_hash(c, case_id)
        h = hashlib.sha256(
            f"{prev}|{case_id}|{ts}|{action}|{payload_str}".encode()
        ).hexdigest()
        c.execute(
            "INSERT INTO audit_entries (id, case_id, timestamp, action, title, subtitle, payload, prev_hash, hash, kind) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (entry_id, case_id, ts, action, title, subtitle, payload_str, prev, h, kind),
        )
    return {
        "id": entry_id,
        "case_id": case_id,
        "timestamp": ts,
        "action": action,
        "title": title,
        "subtitle": subtitle,
        "hash": f"0x{h[:12]}",
        "full_hash": h,
        "prev_hash": prev,
        "kind": kind,
    }


def list_for_case(case_id: str) -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, case_id, timestamp, action, title, subtitle, hash, kind FROM audit_entries WHERE case_id = ? ORDER BY timestamp ASC, id ASC",
            (case_id,),
        ).fetchall()
    return [
        {
            "id": r[0],
            "case_id": r[1],
            "timestamp": r[2],
            "action": r[3],
            "title": r[4],
            "subtitle": r[5],
            "hash": f"0x{r[6][:12]}",
            "full_hash": r[6],
            "kind": r[7],
        }
        for r in rows
    ]
