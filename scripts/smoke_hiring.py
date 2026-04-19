#!/usr/bin/env python3
"""End-to-end hiring round-trip smoke test against a live make-dev stack."""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

LENDER = "http://127.0.0.1:8001"
RECOURSE = "http://127.0.0.1:8000"
CASE = REPO / "scripts" / "seed" / "hiring" / "cases" / "case1"

GREEN = "\033[32m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ok(m): print(f"  {GREEN}✓{RESET} {m}")
def fail(m): print(f"  {RED}✗{RESET} {m}", file=sys.stderr); sys.exit(1)
def step(m): print(f"\n{BOLD}▸ {m}{RESET}")


def reset_and_seed():
    step("Reset + seed hiring case1")
    for p in (
        REPO / "backend" / "recourse.db",
        REPO / "backend" / "recourse.db-wal",
        REPO / "backend" / "recourse.db-shm",
        REPO / "customer_portal" / "backend" / "lender.db",
        REPO / "customer_portal" / "backend" / "lender.db-wal",
        REPO / "customer_portal" / "backend" / "lender.db-shm",
    ):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    for d in (REPO / "backend" / "uploads", REPO / "customer_portal" / "backend" / "uploads"):
        if d.exists():
            shutil.rmtree(d)
    from backend import db as recourse_db
    from customer_portal.backend import db as lender_db
    recourse_db.init_db()
    lender_db.init_db()
    res = subprocess.run([sys.executable, "scripts/seed_hiring.py", "case1"], cwd=REPO, capture_output=True, text=True)
    if res.returncode != 0:
        fail("seed_hiring failed:\n" + (res.stderr or res.stdout))
    ok("seeded Asha")
    time.sleep(0.5)


def first_hiring_app():
    r = httpx.get(f"{LENDER}/api/v1/operator/cases", timeout=5)
    cases = [c for c in r.json()["cases"] if c["id"].startswith("HR-")]
    if not cases:
        fail("no hiring case in operator listing")
    return cases[0]["id"]


def main():
    step("Health checks")
    for label, url in (("LenderCo", LENDER), ("Recourse", RECOURSE)):
        try:
            httpx.get(f"{url}/health", timeout=2).raise_for_status()
        except Exception as e:
            fail(f"{label} not reachable: {e}")
        ok(f"{label} healthy")
    reset_and_seed()
    app_id = first_hiring_app()
    ok(f"hiring app id = {app_id}")

    step("LenderCo issues hiring contest link")
    r = httpx.post(f"{LENDER}/api/v1/hiring/applications/{app_id}/request-contest-link", timeout=5)
    if r.status_code != 200:
        fail(f"contest link failed: {r.text}")
    token = r.json()["contest_url"].split("?t=", 1)[1]
    ok("JWT issued")

    step("Recourse exchanges JWT + DOB")
    with httpx.Client(timeout=60) as client:
        from scripts.seed.hiring.cases.build_all import CASES  # type: ignore
        dob = CASES["case1"]["candidate"]["dob"]
        r = client.post(f"{RECOURSE}/api/v1/contest/open", json={"token": token, "dob": dob})
        if r.status_code != 200:
            fail(f"contest/open failed: {r.text}")
        body = r.json()
        case_id = body["case_id"]
        ok(f"session opened · case_id={case_id}")

        step("Submit text rebuttal for first reason")
        case = client.get(f"{RECOURSE}/api/v1/contest/case").json()
        first_reason_id = case["snapshot"]["shap"][0]["feature"]
        r = client.post(
            f"{RECOURSE}/api/v1/contest/evidence",
            data={
                "target_feature": first_reason_id,
                "doc_type": "recommendation_letter",
                "rebuttal_text": "I have 5+ years of relevant experience including 18 months freelance work delivering Kubernetes-based services in production for fintech clients.",
            },
        )
        if r.status_code != 200:
            fail(f"evidence upload failed: {r.text}")
        verdict = r.json()["validation"]["overall"]
        ok(f"rebuttal accepted; overall={verdict}")

        step("Submit contest")
        r = client.post(f"{RECOURSE}/api/v1/contest/submit")
        if r.status_code != 200:
            fail(f"submit failed: {r.text}")
        body2 = r.json()
        ok(f"outcome={body2['outcome']}  new_verdict={body2['new_decision']['verdict']}")

    step("Verify audit chain")
    r = httpx.get(f"{RECOURSE}/api/v1/audit/{case_id}/verify", timeout=5)
    if r.status_code != 200 or not r.json().get("ok"):
        fail(f"audit verify failed: {r.text}")
    ok(f"chain valid · {r.json()['rows']} rows")

    print(f"\n{GREEN}{BOLD}✓ Hiring smoke passed.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
