"""LenderCo SQLite layer — schema init + per-request connection."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB = _REPO_ROOT / "customer_portal" / "backend" / "lender.db"


def db_path() -> Path:
    return Path(os.environ.get("HELIX_LENDER_DB", _DEFAULT_DB))


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS applicants (
  id              TEXT PRIMARY KEY,
  full_name       TEXT NOT NULL,
  dob             TEXT NOT NULL,
  email           TEXT NOT NULL,
  phone           TEXT,
  created_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
  id              TEXT PRIMARY KEY,
  applicant_id    TEXT NOT NULL REFERENCES applicants(id),
  amount          INTEGER NOT NULL,
  purpose         TEXT,
  status          TEXT NOT NULL CHECK (status IN ('intake','under_review','decided','in_contest','closed')),
  submitted_at    INTEGER NOT NULL,
  decided_at      INTEGER
);

CREATE TABLE IF NOT EXISTS intake_documents (
  id              TEXT PRIMARY KEY,
  application_id  TEXT NOT NULL REFERENCES applications(id),
  doc_type        TEXT NOT NULL,
  original_name   TEXT NOT NULL,
  stored_path     TEXT NOT NULL,
  sha256          TEXT NOT NULL,
  extracted_json  TEXT,
  uploaded_at     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS scored_features (
  application_id  TEXT PRIMARY KEY REFERENCES applications(id),
  feature_vector  TEXT NOT NULL,
  model_version   TEXT NOT NULL,
  scored_at       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
  id              TEXT PRIMARY KEY,
  application_id  TEXT NOT NULL REFERENCES applications(id),
  verdict         TEXT NOT NULL CHECK (verdict IN ('approved','denied')),
  prob_bad        REAL NOT NULL,
  shap_json       TEXT NOT NULL,
  top_reasons     TEXT NOT NULL,
  source          TEXT NOT NULL CHECK (source IN ('initial','recourse_webhook')),
  decided_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS contest_handoffs (
  jti             TEXT PRIMARY KEY,
  application_id  TEXT NOT NULL REFERENCES applications(id),
  issued_at       INTEGER NOT NULL,
  expires_at      INTEGER NOT NULL,
  revoked_at      INTEGER
);

CREATE TABLE IF NOT EXISTS job_postings (
  id              TEXT PRIMARY KEY,
  title           TEXT NOT NULL,
  jd_text         TEXT NOT NULL,
  created_at      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS hiring_applications (
  id              TEXT PRIMARY KEY,
  applicant_id    TEXT NOT NULL REFERENCES applicants(id),
  posting_id      TEXT NOT NULL REFERENCES job_postings(id),
  resume_text     TEXT NOT NULL,
  resume_path     TEXT,
  status          TEXT NOT NULL CHECK (status IN ('intake','decided','in_contest','closed')),
  submitted_at    INTEGER NOT NULL,
  decided_at      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_decisions_app ON decisions(application_id);
CREATE INDEX IF NOT EXISTS idx_hiring_apps_status ON hiring_applications(status);
"""


def init_db() -> None:
    conn = _connect(db_path())
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()


def conn() -> sqlite3.Connection:
    return _connect(db_path())
