#!/usr/bin/env python3
"""End-to-end smoke test.

Assumes ``make dev`` is running. Walks the full Priya Sharma round-trip:

  1. Reset + seed
  2. Issue contest link from LenderCo (mints JWT)
  3. Recourse exchanges JWT + DOB for a session
  4. Upload two pieces of evidence (new payslip + fresh credit report)
  5. Verify both pass the 10-check Evidence Shield
  6. Submit contest → assert outcome flipped
  7. Wait for webhook → assert LenderCo received and persisted
  8. Verify the audit chain hashes cleanly
"""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

LENDER = "http://127.0.0.1:8001"
RECOURSE = "http://127.0.0.1:8000"
CASE_DIR = REPO / "scripts" / "seed" / "loans" / "cases" / "case1"
DOC_DIR = CASE_DIR / "evidence"
PRIYA_APP = "LN-2026-A4F2"
PRIYA_DOB = "1990-03-12"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(msg: str) -> None: print(f"  {GREEN}✓{RESET} {msg}")
def fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}", file=sys.stderr)
    sys.exit(1)
def step(msg: str) -> None: print(f"\n{BOLD}▸ {msg}{RESET}")


def check_health() -> None:
    step("Health checks")
    for label, url in (("LenderCo", LENDER), ("Recourse", RECOURSE)):
        try:
            r = httpx.get(f"{url}/health", timeout=2)
            r.raise_for_status()
        except Exception as exc:
            fail(f"{label} not reachable at {url}: {exc}. Did you run `make dev`?")
        ok(f"{label} healthy")


def reset_and_seed() -> None:
    step("Reset + seed")
    for path in (
        REPO / "backend" / "recourse.db",
        REPO / "backend" / "recourse.db-wal",
        REPO / "backend" / "recourse.db-shm",
        REPO / "customer_portal" / "backend" / "lender.db",
        REPO / "customer_portal" / "backend" / "lender.db-wal",
        REPO / "customer_portal" / "backend" / "lender.db-shm",
    ):
        try: path.unlink()
        except FileNotFoundError: pass
    for d in (REPO / "backend" / "uploads", REPO / "customer_portal" / "backend" / "uploads"):
        if d.exists():
            shutil.rmtree(d)
    ok("databases + uploads wiped")

    # Re-init both schemas immediately so the running uvicorns can read/write.
    from backend import db as recourse_db
    from customer_portal.backend import db as lender_db
    recourse_db.init_db()
    lender_db.init_db()

    res = subprocess.run([sys.executable, "scripts/seed.py"], cwd=REPO, capture_output=True, text=True)
    if res.returncode != 0:
        fail("seed failed:\n" + (res.stderr or res.stdout))
    ok("seeded Priya Sharma case")
    time.sleep(0.5)


def request_contest_link() -> str:
    step("LenderCo issues contest link")
    r = httpx.post(f"{LENDER}/api/v1/applications/{PRIYA_APP}/request-contest-link", timeout=5)
    if r.status_code != 200:
        fail(f"request-contest-link failed: {r.status_code} {r.text}")
    body = r.json()
    if "contest_url" not in body or "?t=" not in body["contest_url"]:
        fail(f"unexpected response: {body}")
    token = body["contest_url"].split("?t=", 1)[1]
    ok(f"JWT issued (jti {body['jti'][:12]}…)")
    return token


def open_recourse_session(client: httpx.Client, token: str) -> dict:
    step("Recourse exchanges JWT + DOB for session")
    r = client.post(f"{RECOURSE}/api/v1/contest/open", json={"token": token, "dob": PRIYA_DOB}, timeout=10)
    if r.status_code != 200:
        fail(f"contest/open failed: {r.status_code} {r.text}")
    body = r.json()
    ok(f"session opened · case_id={body['case_id']}")
    return body


def upload_evidence(client: httpx.Client, target_feature: str, doc_type: str, filename: str) -> dict:
    step(f"Upload {filename} → target {target_feature}")
    src = DOC_DIR / filename
    if not src.exists():
        fail(f"missing demo PDF: {src}")
    files = {"file": (filename, src.read_bytes(), "application/pdf")}
    data = {"target_feature": target_feature, "doc_type": doc_type}
    r = client.post(f"{RECOURSE}/api/v1/contest/evidence", files=files, data=data, timeout=20)
    if r.status_code != 200:
        fail(f"evidence upload failed: {r.status_code} {r.text}")
    body = r.json()
    overall = body["validation"]["overall"]
    if overall != "accepted":
        failed_checks = [c for c in body["validation"]["checks"] if not c["passed"]]
        fail(f"shield {overall} for {filename}: {failed_checks}")
    ok(f"shield accepted (extracted_value={body.get('extracted_value')})")
    return body


def submit_contest(client: httpx.Client) -> dict:
    step("Submit contest → re-evaluate")
    r = client.post(f"{RECOURSE}/api/v1/contest/submit", timeout=10)
    if r.status_code != 200:
        fail(f"submit failed: {r.status_code} {r.text}")
    body = r.json()
    ok(f"outcome={body['outcome']} new_verdict={body['new_decision']['verdict']} prob_bad={body['new_decision']['prob_bad']:.3f}")
    if body["outcome"] != "flipped":
        fail(f"expected flipped, got {body['outcome']}")
    return body


def wait_webhook(case_id: str, deadline_s: float = 8.0) -> None:
    step("Wait for verdict webhook delivery")
    deadline = time.time() + deadline_s
    while time.time() < deadline:
        r = httpx.get(f"{LENDER}/api/v1/operator/cases/{case_id}", timeout=5)
        if r.status_code == 200:
            decisions = r.json().get("decisions") or []
            if any(d["source"] == "recourse_webhook" for d in decisions):
                ok("LenderCo persisted Recourse verdict")
                return
        time.sleep(0.5)
    fail("webhook never landed")


def verify_audit(case_id_recourse: str) -> None:
    step("Verify audit chain")
    r = httpx.get(f"{RECOURSE}/api/v1/audit/{case_id_recourse}/verify", timeout=5)
    if r.status_code != 200:
        fail(f"audit verify failed: {r.status_code}")
    body = r.json()
    if not body.get("ok"):
        fail(f"audit chain broken: {body}")
    ok(f"chain valid · {body['rows']} rows · head {body['head'][:16]}…")


def main() -> int:
    check_health()
    reset_and_seed()
    token = request_contest_link()
    with httpx.Client(timeout=20) as client:
        session = open_recourse_session(client, token)
        upload_evidence(client, "MonthlyIncome", "payslip", "payslip_promotion.pdf")
        upload_evidence(client, "RevolvingUtilizationOfUnsecuredLines", "credit_report", "credit_report_repaired.pdf")
        result = submit_contest(client)
    wait_webhook(PRIYA_APP)
    verify_audit(session["case_id"])
    print(f"\n{GREEN}{BOLD}✓ End-to-end smoke passed.{RESET}")
    print(f"  outcome={result['outcome']}  new_verdict={result['new_decision']['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
