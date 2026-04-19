#!/usr/bin/env python3
"""Seed the LenderCo database with one or more demo cases.

Each case folder under ``scripts/seed/loans/cases/`` ships a ``case.json``
spec plus intake/evidence/adversarial PDFs. ``seed.py`` reads the spec,
copies intake docs into the LenderCo uploads dir, runs the shared OCR
pipeline so extraction noise is exercised, applies the spec's
``intake_features`` overrides for deterministic demo behavior, scores via
the real XGBoost adapter, and writes the resulting decision.

Usage:

    scripts/seed.py                # seed case1 (default)
    scripts/seed.py case2          # seed only case2
    scripts/seed.py --all          # seed every case found
"""
from __future__ import annotations

import argparse
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

CASES_DIR = REPO / "scripts" / "seed" / "loans" / "cases"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ensure_pdfs() -> None:
    sample = CASES_DIR / "case1" / "intake" / "payslip.pdf"
    if sample.exists():
        return
    print("Generating case fixtures…")
    from scripts.seed.loans.cases import build_all  # type: ignore
    build_all.main()


def list_cases() -> list[str]:
    if not CASES_DIR.exists():
        return []
    return sorted(p.name for p in CASES_DIR.iterdir() if (p / "case.json").exists())


def seed_case(case_name: str) -> None:
    case_dir = CASES_DIR / case_name
    spec_path = case_dir / "case.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"No case.json at {spec_path}")
    spec = json.loads(spec_path.read_text())

    lender_db.init_db()
    uploads_dir = REPO / "customer_portal" / "backend" / "uploads" / spec["application_id"]
    uploads_dir.mkdir(parents=True, exist_ok=True)

    now = int(time.time())
    doc_records: list[dict] = []

    with lender_db.conn() as c:
        existing = c.execute("SELECT 1 FROM applications WHERE id = ?", (spec["application_id"],)).fetchone()
        if existing:
            print(f"  · already seeded: {spec['application_id']}")
            return

        c.execute(
            "INSERT OR REPLACE INTO applicants (id, full_name, dob, email, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (spec["applicant_id"], spec["name"], spec["dob"], spec["email"], spec.get("phone"), now),
        )
        c.execute(
            "INSERT INTO applications (id, applicant_id, amount, purpose, status, submitted_at) VALUES (?, ?, ?, ?, 'intake', ?)",
            (spec["application_id"], spec["applicant_id"], spec["amount"], spec["purpose"], now),
        )

        for d in spec["intake_documents"]:
            src = case_dir / d["file"]
            if not src.exists():
                raise FileNotFoundError(f"Missing intake doc: {src}")
            doc_id = "doc_" + uuid.uuid4().hex[:12]
            dst = uploads_dir / f"{doc_id}.pdf"
            shutil.copy2(src, dst)
            extracted = intake.extract_doc(dst, d["doc_type"])
            c.execute(
                "INSERT INTO intake_documents (id, application_id, doc_type, original_name, stored_path, sha256, extracted_json, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (doc_id, spec["application_id"], d["doc_type"], Path(d["file"]).name, str(dst), _sha256(dst), json.dumps(extracted), now),
            )
            doc_records.append(extracted)

    features = intake.assemble_features(domain="loans", applicant_dob=spec["dob"], doc_records=doc_records)
    features.update(spec.get("intake_features", {}))
    scored = scorer.score("loans", features)

    now = int(time.time())
    decision_id = "dec_" + uuid.uuid4().hex[:12]
    with lender_db.conn() as c:
        c.execute(
            "INSERT INTO scored_features (application_id, feature_vector, model_version, scored_at) VALUES (?, ?, ?, ?)",
            (spec["application_id"], json.dumps(features), scored["model_version"], now),
        )
        c.execute(
            "INSERT INTO decisions (id, application_id, verdict, prob_bad, shap_json, top_reasons, source, decided_at) VALUES (?, ?, ?, ?, ?, ?, 'initial', ?)",
            (decision_id, spec["application_id"], scored["verdict"], scored["prob_bad"], json.dumps(scored["shap"]), json.dumps(scored["top_reasons"]), now),
        )
        c.execute("UPDATE applications SET status = 'decided', decided_at = ? WHERE id = ?", (now, spec["application_id"]))

    pad = " " * 4
    print(f"\n{pad}{spec['name']}")
    print(f"{pad}Case ref:  {spec['application_id']}")
    print(f"{pad}DOB:       {spec['dob']}")
    print(f"{pad}Verdict:   {scored['verdict'].upper()} · prob_bad={scored['prob_bad']:.3f}")
    if spec.get("story"):
        print(f"{pad}Story:     {spec['story']}")
    if spec.get("evidence_catalog"):
        print(f"{pad}Evidence:  {len(spec['evidence_catalog'])} clean files in {case_dir / 'evidence'}")
    if spec.get("adversarial_catalog"):
        print(f"{pad}Adversarial: {len(spec['adversarial_catalog'])} files in {case_dir / 'adversarial'} (designed to fail Evidence Shield)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed LenderCo demo cases.")
    parser.add_argument("case", nargs="?", default="case1", help="Case folder name (default: case1)")
    parser.add_argument("--all", action="store_true", help="Seed every case under scripts/seed/loans/cases")
    args = parser.parse_args()

    _ensure_pdfs()

    cases = list_cases()
    if not cases:
        print("No cases found. Did build_all run?", file=sys.stderr)
        sys.exit(2)

    if args.all:
        for name in cases:
            print(f"\n▸ Seeding {name}")
            seed_case(name)
    else:
        if args.case not in cases:
            print(f"Unknown case '{args.case}'. Available: {', '.join(cases)}", file=sys.stderr)
            sys.exit(2)
        print(f"▸ Seeding {args.case}")
        seed_case(args.case)

    print()
    print("  Visit http://localhost:5174/?view=operator to inspect cases.")
    print("  Click any denied case → 'Issue contest link' → opens Recourse on :5173.")


if __name__ == "__main__":
    main()
