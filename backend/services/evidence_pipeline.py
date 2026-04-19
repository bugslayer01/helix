"""Glue between uploaded evidence and the Evidence Shield.

For every upload:
1. Write bytes to ``backend/uploads/{case}/{uuid}.{ext}``, compute SHA-256.
2. Route extraction through ``shared.ocr.router`` using the adapter's prompt.
3. Build an ``EvidenceContext`` and run ``shield.run_shield``.
4. Persist the evidence row, the validation report, and (if accepted) a proposal.
5. Append audit rows at each step.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from backend import db as _db
from backend.services import audit_log
from shared.adapters import get_adapter
from shared.ocr import extract as ocr_extract
from shared.validators import run_shield
from shared.validators.types import EvidenceContext


def _uploads_root() -> Path:
    return Path(os.environ.get("HELIX_RECOURSE_UPLOADS", "backend/uploads"))


def _store_file(case_id: str, filename: str, blob: bytes) -> tuple[Path, str]:
    sha = hashlib.sha256(blob).hexdigest()
    ext = Path(filename).suffix or ".bin"
    evidence_id = "ev_" + uuid.uuid4().hex[:12]
    target_dir = _uploads_root() / case_id
    target_dir.mkdir(parents=True, exist_ok=True)
    stored_path = target_dir / f"{evidence_id}{ext}"
    stored_path.write_bytes(blob)
    return stored_path, sha


def _replay_hit(conn, sha: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM evidence_hash_index WHERE sha256 = ?", (sha,)).fetchone()
    if not row:
        return None
    return {"sha256": row["sha256"], "first_seen_at": row["first_seen_at"], "first_case_id": row["first_case_id"], "seen_count": row["seen_count"]}


def _prior_evidence(conn, case_id: str, target_feature: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, extracted_value FROM evidence WHERE case_id = ? AND target_feature = ?",
        (case_id, target_feature),
    ).fetchall()
    return [{"id": r["id"], "extracted_value": r["extracted_value"]} for r in rows if r["extracted_value"] is not None]


def _update_hash_index(conn, sha: str, case_id: str, now: int) -> None:
    row = conn.execute("SELECT sha256 FROM evidence_hash_index WHERE sha256 = ?", (sha,)).fetchone()
    if row:
        conn.execute("UPDATE evidence_hash_index SET seen_count = seen_count + 1 WHERE sha256 = ?", (sha,))
    else:
        conn.execute(
            "INSERT INTO evidence_hash_index (sha256, first_seen_at, first_case_id, seen_count) VALUES (?, ?, ?, 1)",
            (sha, now, case_id),
        )


def process_upload(
    *,
    case_id: str,
    target_feature: str,
    doc_type: str,
    original_name: str,
    blob: bytes,
    rebuttal_text: str | None = None,
) -> dict[str, Any]:
    """Full pipeline. Returns a dict with evidence id, extracted value, and the shield report."""
    if not blob:
        raise ValueError("empty_upload")

    # 1. Persist bytes first so we have stable SHA-256 and path even if OCR fails.
    stored_path, sha = _store_file(case_id, original_name, blob)
    evidence_id = stored_path.stem  # "ev_xxxx"
    now = int(time.time())

    audit_log.append(
        case_id,
        "evidence_uploaded",
        {
            "evidence_id": evidence_id,
            "target_feature": target_feature,
            "doc_type": doc_type,
            "sha256": sha,
            "original_name": original_name,
        },
    )

    # 2. Extraction
    adapter = get_adapter("loans")
    prompt_spec = adapter.extract_prompt(doc_type)
    # Text-only rebuttals (no real file) skip OCR — the blob is just the
    # rebuttal text encoded to bytes and not a renderable document.
    text_only = rebuttal_text is not None and stored_path.suffix.lower() == ".txt"
    if text_only:
        from shared.ocr.router import ExtractionResult  # local import to avoid cycles
        extraction = ExtractionResult(
            doc_type=doc_type,
            fields={},
            text_layer=rebuttal_text or "",
            source="rebuttal-text",
            confidence=1.0,
            notes=[],
        )
    else:
        extraction = ocr_extract(
            stored_path,
            expected_doc_type=doc_type,
            schema=prompt_spec.get("schema"),
            prompt=prompt_spec.get("prompt"),
        )
    fields = extraction.fields or {}
    feature_field = prompt_spec.get("feature_field")
    claimed_value: float | None = None
    if feature_field and feature_field in fields:
        try:
            claimed_value = float(fields[feature_field])
        except (TypeError, ValueError):
            claimed_value = None

    # 3. Load case snapshot + prior evidence for context
    with _db.conn() as c:
        case_row = c.execute("SELECT * FROM contest_cases WHERE id = ?", (case_id,)).fetchone()
        if not case_row:
            raise ValueError("case_not_found")
        snapshot_features = json.loads(case_row["snapshot_features"])
        replay_hit = _replay_hit(c, sha)
        prior_evidence_for_feature = _prior_evidence(c, case_id, target_feature)

    prior_value = snapshot_features.get(target_feature)
    try:
        prior_value_f = float(prior_value) if prior_value is not None else None
    except (TypeError, ValueError):
        prior_value_f = None

    # 4. Bounds + delta multiplier from the adapter schema
    feature_bounds = (None, None)
    delta_mult = 3.0
    for spec in adapter.feature_schema():
        if spec["feature"] == target_feature:
            feature_bounds = (spec.get("min"), spec.get("max"))
            delta_mult = float(spec.get("realistic_delta_multiplier", 3.0))
            break

    ctx = EvidenceContext(
        case_id=case_id,
        target_feature=target_feature,
        claimed_value=claimed_value,
        prior_value=prior_value_f,
        upload_path=str(stored_path),
        upload_sha256=sha,
        doc_type_expected=doc_type,
        extraction_fields=fields,
        extraction_text_layer=extraction.text_layer,
        extraction_confidence=extraction.confidence,
        feature_bounds=feature_bounds,
        realistic_delta_multiplier=delta_mult,
        prior_evidence_for_feature=prior_evidence_for_feature,
        replay_index_hit=replay_hit,
        extraction_source=extraction.source,
    )

    if text_only:
        # Text-only rebuttals have no document to scan — emit a synthetic
        # accepted report so the adapter still sees the narrative.
        from shared.validators.shield import ValidationReport
        from shared.validators.types import CheckResult
        report = ValidationReport(
            overall="accepted",
            summary="Text-only rebuttal accepted for adapter review.",
            checks=[
                CheckResult(
                    name="rebuttal_text",
                    passed=True,
                    severity="low",
                    detail="Free-text rebuttal recorded for adjudicator review.",
                )
            ],
        )
    else:
        report = run_shield(ctx)

    # 5. Persist evidence + validation + (maybe) proposal
    with _db.conn() as c:
        c.execute(
            """
            INSERT INTO evidence (id, case_id, target_feature, doc_type, stored_path, sha256, extracted_json, extracted_value, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                case_id,
                target_feature,
                fields.get("doc_type") or doc_type,
                str(stored_path),
                sha,
                json.dumps({
                    "fields": fields,
                    "text_layer": extraction.text_layer[:5000],
                    "source": extraction.source,
                    "confidence": extraction.confidence,
                    "notes": extraction.notes,
                    "rebuttal_text": rebuttal_text,
                }),
                claimed_value,
                now,
            ),
        )
        c.execute(
            """
            INSERT INTO evidence_validations (evidence_id, checks_json, overall, summary, validated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                json.dumps([c.to_dict() for c in report.checks]),
                report.overall,
                report.summary,
                now,
            ),
        )
        _update_hash_index(c, sha, case_id, now)

        proposal_id = None
        if report.overall == "accepted":
            create_proposal = (claimed_value is not None and prior_value_f is not None) or rebuttal_text
            if create_proposal:
                proposal_id = "pr_" + uuid.uuid4().hex[:12]
                c.execute(
                    "INSERT INTO proposals (id, case_id, feature, original_value, proposed_value, evidence_id, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'validated', ?)",
                    (proposal_id, case_id, target_feature, prior_value_f or 0.0, claimed_value or 0.0, evidence_id, now),
                )
        c.execute("UPDATE contest_cases SET status = 'evidence_review' WHERE id = ? AND status = 'open'", (case_id,))

    audit_log.append(
        case_id,
        "validator_ran",
        {
            "evidence_id": evidence_id,
            "overall": report.overall,
            "summary": report.summary,
            "failed_checks": [c.to_dict() for c in report.checks if not c.passed],
        },
    )
    if report.overall == "rejected":
        audit_log.append(case_id, "evidence_rejected", {"evidence_id": evidence_id, "summary": report.summary})
    elif report.overall == "accepted" and proposal_id:
        audit_log.append(
            case_id,
            "proposal_validated",
            {
                "proposal_id": proposal_id,
                "feature": target_feature,
                "original": prior_value_f,
                "proposed": claimed_value,
            },
        )

    return {
        "evidence_id": evidence_id,
        "doc_type": fields.get("doc_type") or doc_type,
        "extracted_value": claimed_value,
        "extracted_fields": fields,
        "extraction_source": extraction.source,
        "extraction_confidence": extraction.confidence,
        "validation": report.to_dict(),
        "proposal_id": proposal_id,
    }


def delete_evidence(case_id: str, evidence_id: str) -> bool:
    with _db.conn() as c:
        row = c.execute(
            "SELECT stored_path FROM evidence WHERE id = ? AND case_id = ?",
            (evidence_id, case_id),
        ).fetchone()
        if not row:
            return False
        c.execute("DELETE FROM proposals WHERE evidence_id = ?", (evidence_id,))
        c.execute("DELETE FROM evidence_validations WHERE evidence_id = ?", (evidence_id,))
        c.execute("DELETE FROM evidence WHERE id = ?", (evidence_id,))
    try:
        Path(row["stored_path"]).unlink(missing_ok=True)
    except Exception:
        pass
    audit_log.append(case_id, "evidence_removed", {"evidence_id": evidence_id})
    return True
