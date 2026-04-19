#!/usr/bin/env python3
"""Seed LenderCo with hiring postings + candidates from scripts/seed/hiring/cases/."""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from customer_portal.backend import db as lender_db
from customer_portal.backend.services import hiring_intake

CASES_DIR = REPO / "scripts" / "seed" / "hiring" / "cases"


def list_cases() -> list[str]:
    return sorted(p.name for p in CASES_DIR.iterdir() if (p / "case.json").exists())


def seed_case(case_name: str) -> None:
    case_dir = CASES_DIR / case_name
    spec = json.loads((case_dir / "case.json").read_text())
    jd_text = (case_dir / "jd.txt").read_text()
    resume_path = case_dir / "resume.pdf"

    lender_db.init_db()
    posting_id = "JOB-2026-" + uuid.uuid4().hex[:6].upper()
    application_id = "HR-2026-" + uuid.uuid4().hex[:4].upper()
    applicant_id = "CAN-" + uuid.uuid4().hex[:8].upper()
    now = int(time.time())

    resume_text = hiring_intake.extract_resume_text(resume_path)
    scored = hiring_intake.score_application(jd_text, resume_text)
    decision_id = "dec_" + uuid.uuid4().hex[:12]

    with lender_db.conn() as c:
        c.execute("INSERT INTO job_postings (id, title, jd_text, created_at) VALUES (?, ?, ?, ?)",
                  (posting_id, spec["posting_title"], jd_text, now))
        c.execute("INSERT INTO applicants (id, full_name, dob, email, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  (applicant_id, spec["candidate"]["full_name"], spec["candidate"]["dob"], spec["candidate"]["email"], None, now))
        # Insert applications row FIRST so scored_features + decisions FK references resolve.
        c.execute("INSERT INTO applications (id, applicant_id, amount, purpose, status, submitted_at, decided_at) VALUES (?, ?, 0, ?, 'decided', ?, ?)",
                  (application_id, applicant_id, f"hiring · {spec['posting_title']}", now, now))
        c.execute("INSERT INTO hiring_applications (id, applicant_id, posting_id, resume_text, resume_path, status, submitted_at, decided_at) VALUES (?, ?, ?, ?, ?, 'decided', ?, ?)",
                  (application_id, applicant_id, posting_id, resume_text, str(resume_path), now, now))
        c.execute("INSERT INTO scored_features (application_id, feature_vector, model_version, scored_at) VALUES (?, ?, ?, ?)",
                  (application_id, json.dumps({"posting_id": posting_id}), scored["model_version"], now))
        c.execute("INSERT INTO decisions (id, application_id, verdict, prob_bad, shap_json, top_reasons, source, decided_at) VALUES (?, ?, ?, ?, ?, ?, 'initial', ?)",
                  (decision_id, application_id, scored["verdict"], scored["prob_bad"], json.dumps(scored["shap"]), json.dumps(scored["top_reasons"]), now))

    print(f"  {spec['candidate']['full_name']:24s} {scored['verdict'].upper():>9s} fit={scored['confidence']:.2f}  app={application_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", nargs="?", default=None)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    cases = list_cases()
    if not cases:
        print("No hiring cases. Run build_all first.", file=sys.stderr)
        sys.exit(2)
    if args.all or not args.case:
        for n in cases:
            print(f"▸ Seeding {n}")
            seed_case(n)
    else:
        seed_case(args.case)


if __name__ == "__main__":
    main()
