"""Build 3 hiring case fixtures (JD + resume + case.json)."""
from __future__ import annotations

import json
from pathlib import Path

from . import _lib

HERE = Path(__file__).resolve().parent

CASES = {
    "case1": {
        "posting_title": "Senior Backend Engineer",
        "jd_text": (
            "About the role:\n"
            "We are hiring a Senior Backend Engineer to own our Python services platform.\n\n"
            "Requirements:\n"
            "- 5+ years backend engineering experience\n"
            "- Strong Python (FastAPI / Django) + Postgres\n"
            "- Hands-on Kubernetes in production\n"
            "- Bachelor's degree in CS or equivalent\n"
            "- Comfortable owning on-call rotation\n\n"
            "Nice to have: Go, gRPC, observability tooling."
        ),
        "candidate": {"full_name": "Asha Verma", "dob": "1995-08-22", "email": "helix-asha@mailinator.com"},
        "resume": {
            "name": "Asha Verma",
            "email": "helix-asha@mailinator.com",
            "summary": "Backend engineer with 3 years of experience building Python services. Looking for a senior role.",
            "experience": [
                "<b>Backend Engineer · Razorpay (2024-present)</b> · Built REST APIs in FastAPI, Postgres schema design, deployed to AWS ECS.",
                "<b>Software Engineer · Freshworks (2022-2024)</b> · Django monolith maintenance. Wrote integration tests.",
            ],
            "skills": ["Python", "FastAPI", "Postgres", "Docker", "AWS ECS", "Git"],
            "education": "B.Tech Computer Science · NIT Trichy · 2022",
        },
        "story": "Strong Python but missing Kubernetes + only 3 yrs vs 5+ required. Designed to be denied then flippable with a CKA cert + freelance contracting evidence.",
    },
    "case2": {
        "posting_title": "Engineering Manager",
        "jd_text": (
            "About the role:\n"
            "Engineering Manager for a 12-person platform team.\n\n"
            "Requirements:\n"
            "- 8+ years total engineering experience\n"
            "- 3+ years managing engineers (hiring, perf, mentoring)\n"
            "- Has shipped distributed systems at scale (>1M req/day)\n"
            "- Master's degree preferred\n"
            "- Strong written communication\n"
        ),
        "candidate": {"full_name": "Devansh Kapoor", "dob": "1988-04-11", "email": "helix-devansh@mailinator.com"},
        "resume": {
            "name": "Devansh Kapoor",
            "email": "helix-devansh@mailinator.com",
            "summary": "Senior IC with 9 years building backend systems. No formal management title yet but mentored 4 juniors.",
            "experience": [
                "<b>Staff Engineer · Flipkart (2021-present)</b> · Owned recommendations service handling 4M req/day. Mentored 4 SDE-2 engineers.",
                "<b>Senior Engineer · Cleartrip (2017-2021)</b> · Booking pipeline rewrite, shaved 40% latency.",
                "<b>Engineer · Slideshare (2015-2017)</b> · Backend.",
            ],
            "skills": ["Java", "Go", "Kafka", "AWS", "System design", "Mentoring"],
            "education": "B.Tech IIT Bombay · 2015",
        },
        "story": "Strong IC depth and mentoring but no management title and no Master's. Held outcome — model says still IC, not yet manager.",
    },
    "case3": {
        "posting_title": "Junior Data Analyst",
        "jd_text": (
            "About the role:\n"
            "Junior Data Analyst on the growth team.\n\n"
            "Requirements:\n"
            "- 0-2 years experience\n"
            "- SQL and one of (Python | R)\n"
            "- Comfortable with dashboards (Looker / Metabase)\n"
            "- Bachelor's in any quantitative field\n"
        ),
        "candidate": {"full_name": "Rhea Joshi", "dob": "2002-01-15", "email": "helix-rhea@mailinator.com"},
        "resume": {
            "name": "Rhea Joshi",
            "email": "helix-rhea@mailinator.com",
            "summary": "Recent grad with 1 year as a part-time analytics intern at a fintech. Loves Python + SQL.",
            "experience": [
                "<b>Analytics Intern · Zerodha (2024-2025)</b> · SQL queries on PostgreSQL, dashboards in Metabase, ad-hoc Python notebooks.",
                "<b>Data Science Club · IIIT Hyderabad (2022-2024)</b> · Led Kaggle study group, ran weekly SQL sessions.",
            ],
            "skills": ["SQL", "Python", "Pandas", "Metabase", "Excel"],
            "education": "B.Tech Information Technology · IIIT Hyderabad · 2025",
        },
        "story": "Approved at intake. Demos the LLM judge accepting cleanly without contest.",
    },
}


def build_case(name: str, spec: dict) -> None:
    case_dir = HERE / name
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "jd.txt").write_text(spec["jd_text"])
    _lib.render_resume(case_dir / "resume.pdf", **spec["resume"])
    (case_dir / "case.json").write_text(json.dumps({
        "posting_title": spec["posting_title"],
        "jd_text": spec["jd_text"],
        "candidate": spec["candidate"],
        "story": spec["story"],
    }, indent=2))
    print(f"  built {name}: {spec['candidate']['full_name']} for {spec['posting_title']}")


def main() -> None:
    print("Generating hiring fixtures…")
    for name, spec in CASES.items():
        build_case(name, spec)
    print(f"Done. {len(CASES)} cases at {HERE}")


if __name__ == "__main__":
    main()
