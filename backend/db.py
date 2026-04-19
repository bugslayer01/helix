"""Recourse SQLite layer — schema init + per-request connection."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = _REPO_ROOT / "backend" / "recourse.db"


def db_path() -> Path:
    return Path(os.environ.get("HELIX_RECOURSE_DB", _DEFAULT_DB))


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS contest_cases (
  id                 TEXT PRIMARY KEY,
  customer_id        TEXT NOT NULL,
  external_case_id   TEXT NOT NULL,
  external_ref       TEXT NOT NULL,
  applicant_display  TEXT NOT NULL,
  applicant_dob_hash TEXT NOT NULL,
  snapshot_features  TEXT NOT NULL,
  snapshot_decision  TEXT NOT NULL,
  snapshot_shap      TEXT NOT NULL,
  model_version      TEXT NOT NULL,
  status             TEXT NOT NULL CHECK (status IN (
                       'open','evidence_review','re_evaluating',
                       'verdict_held','verdict_flipped','closed','revoked'
                     )),
  created_at         INTEGER NOT NULL,
  closed_at          INTEGER,
  UNIQUE (customer_id, external_case_id)
);

CREATE TABLE IF NOT EXISTS sessions (
  id              TEXT PRIMARY KEY,
  case_id         TEXT NOT NULL REFERENCES contest_cases(id),
  jti             TEXT NOT NULL,
  created_at      INTEGER NOT NULL,
  expires_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS used_jti (
  jti             TEXT PRIMARY KEY,
  consumed_at     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
  id              TEXT PRIMARY KEY,
  case_id         TEXT NOT NULL REFERENCES contest_cases(id),
  target_feature  TEXT NOT NULL,
  doc_type        TEXT,
  stored_path     TEXT NOT NULL,
  sha256          TEXT NOT NULL,
  extracted_json  TEXT,
  extracted_value REAL,
  uploaded_at     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_validations (
  evidence_id     TEXT PRIMARY KEY REFERENCES evidence(id),
  checks_json     TEXT NOT NULL,
  overall         TEXT NOT NULL CHECK (overall IN ('accepted','flagged','rejected')),
  summary         TEXT NOT NULL,
  validated_at    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS proposals (
  id              TEXT PRIMARY KEY,
  case_id         TEXT NOT NULL REFERENCES contest_cases(id),
  feature         TEXT NOT NULL,
  original_value  REAL NOT NULL,
  proposed_value  REAL NOT NULL,
  evidence_id     TEXT REFERENCES evidence(id),
  status          TEXT NOT NULL CHECK (status IN ('validated','applied','rejected')),
  created_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS verdict_webhooks (
  id              TEXT PRIMARY KEY,
  case_id         TEXT NOT NULL REFERENCES contest_cases(id),
  new_decision    TEXT NOT NULL,
  new_prob_bad    REAL NOT NULL,
  new_features    TEXT NOT NULL,
  delta_json      TEXT NOT NULL,
  delivered_at    INTEGER,
  attempts        INTEGER NOT NULL DEFAULT 0,
  last_error      TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id         TEXT NOT NULL,
  action          TEXT NOT NULL,
  payload_json    TEXT NOT NULL,
  prev_hash       TEXT NOT NULL,
  hash            TEXT NOT NULL,
  created_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_hash_index (
  sha256          TEXT PRIMARY KEY,
  first_seen_at   INTEGER NOT NULL,
  first_case_id   TEXT NOT NULL,
  seen_count      INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_sessions_case ON sessions(case_id);
CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_log(case_id, id);
CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence(case_id);
CREATE INDEX IF NOT EXISTS idx_proposals_case ON proposals(case_id);
"""


_initialized_paths: set[str] = set()


def init_db() -> None:
    path = db_path()
    conn = _connect(path)
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()
    _initialized_paths.add(str(path.resolve()))


def conn() -> sqlite3.Connection:
    path = db_path()
    key = str(path.resolve())
    if key not in _initialized_paths or not path.exists():
        init_db()
    return _connect(path)
