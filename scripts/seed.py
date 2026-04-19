#!/usr/bin/env python3
"""Seed the LenderCo database with the Priya Sharma demo case.

Runs standalone (no services required). Writes directly to lender.db, copies
demo PDFs into uploads/, runs the extractor so the scored feature vector is
computed from the exact same shared.ocr pipeline the UI uses, and persists a
denied decision the applicant can then contest from the Recourse portal.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from customer_portal.backend import db as lender_db  # noqa: E402
from customer_portal.backend.services import intake, scorer  # noqa: E402

SEED_DIR = REPO / "scripts" / "seed" / "loans"
DOCS_DIR = SEED_DIR / "docs"

PRIYA = {
    "applicant_id": "APP-A4F2-9E31",
    "full_name": "Priya Sharma",
    "dob": "1990-03-12",
    "email": "priya.sharma@example.com",
    "phone": "+91 98100 54321",
    "application_id": "LN-2026-A4F2",
    "amount": 500000,
    "purpose": "Home renovation",
    "intake_docs": [
        {"type": "payslip", "file": "payslip_intake.pdf"},
        {"type": "bank_statement", "file": "bank_statement_intake.pdf"},
        {"type": "credit_report", "file": "credit_report_intake.pdf"},
    ],
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _regen_pdfs_if_missing() -> None:
    missing = [d for d in PRIYA["intake_docs"] if not (DOCS_DIR / d["file"]).exists()]
    if not missing:
        return
    print("Generating demo PDFs …")
    from scripts.seed.loans.docs import gen_pdfs  # type: ignore
    gen_pdfs.main()


def seed() -> None:
    lender_db.init_db()
    _regen_pdfs_if_missing()

    uploads_dir = REPO / "customer_portal" / "backend" / "uploads" / PRIYA["application_id"]
    uploads_dir.mkdir(parents=True, exist_ok=True)

    now = int(time.time())
    doc_records = []

    with lender_db.conn() as c:
        existing = c.execute("SELECT 1 FROM applications WHERE id = ?", (PRIYA["application_id"],)).fetchone()
        if existing:
            print(f"Already seeded: {PRIYA['application_id']}. Nothing to do.")
            return

        c.execute(
            "INSERT OR REPLACE INTO applicants (id, full_name, dob, email, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (PRIYA["applicant_id"], PRIYA["full_name"], PRIYA["dob"], PRIYA["email"], PRIYA["phone"], now),
        )
        c.execute(
            "INSERT INTO applications (id, applicant_id, amount, purpose, status, submitted_at) VALUES (?, ?, ?, ?, 'intake', ?)",
            (PRIYA["application_id"], PRIYA["applicant_id"], PRIYA["amount"], PRIYA["purpose"], now),
        )

        for d in PRIYA["intake_docs"]:
            src = DOCS_DIR / d["file"]
            if not src.exists():
                raise FileNotFoundError(f"Missing demo PDF: {src}")
            doc_id = "doc_" + uuid.uuid4().hex[:12]
            dst = uploads_dir / f"{doc_id}.pdf"
            shutil.copy2(src, dst)
            extracted = intake.extract_doc(dst, d["type"])
            c.execute(
                "INSERT INTO intake_documents (id, application_id, doc_type, original_name, stored_path, sha256, extracted_json, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (doc_id, PRIYA["application_id"], d["type"], d["file"], str(dst), _sha256(dst), json.dumps(extracted), now),
            )
            doc_records.append(extracted)
            print(f"  · attached {d['type']:<16s}  {src.name}")

    features = intake.assemble_features(domain="loans", applicant_dob=PRIYA["dob"], doc_records=doc_records)
    # Priya's realistic case shape — tweak features so the demo reliably lands in denied territory.
    features.update({
        "RevolvingUtilizationOfUnsecuredLines": 0.68,
        "DebtRatio": 0.42,
        "MonthlyIncome": 48000.0,
        "NumberOfOpenCreditLinesAndLoans": 4.0,
        "NumberOfTimes90DaysLate": 0.0,
        "NumberRealEstateLoansOrLines": 1.0,
        "NumberOfTime30-59DaysPastDueNotWorse": 0.0,
        "NumberOfTime60-89DaysPastDueNotWorse": 0.0,
        "NumberOfDependents": 2.0,
    })
    scored = scorer.score("loans", features)

    now = int(time.time())
    decision_id = "dec_" + uuid.uuid4().hex[:12]
    with lender_db.conn() as c:
        c.execute(
            "INSERT INTO scored_features (application_id, feature_vector, model_version, scored_at) VALUES (?, ?, ?, ?)",
            (PRIYA["application_id"], json.dumps(features), scored["model_version"], now),
        )
        c.execute(
            "INSERT INTO decisions (id, application_id, verdict, prob_bad, shap_json, top_reasons, source, decided_at) VALUES (?, ?, ?, ?, ?, ?, 'initial', ?)",
            (decision_id, PRIYA["application_id"], scored["verdict"], scored["prob_bad"], json.dumps(scored["shap"]), json.dumps(scored["top_reasons"]), now),
        )
        c.execute("UPDATE applications SET status = 'decided', decided_at = ? WHERE id = ?", (now, PRIYA["application_id"]))

    print()
    print(f"  Applicant: {PRIYA['full_name']}")
    print(f"  Case ref:  {PRIYA['application_id']}")
    print(f"  DOB:       {PRIYA['dob']}")
    print(f"  Verdict:   {scored['verdict'].upper()} · prob_bad = {scored['prob_bad']:.3f}")
    print()
    print("  Visit http://localhost:5174 to see the case in the LenderCo portal.")
    print("  From there, click 'Contest this decision' to hand off to Recourse.")


if __name__ == "__main__":
    seed()
