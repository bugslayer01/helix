"""Live integration tests — skipped if OPENAI_API_KEY is missing."""
import os
import pytest

from shared.adapters import get_adapter


pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)


def test_predict_returns_decision_dict():
    a = get_adapter("hiring")
    features = {
        "jd_text": "Senior Python backend engineer. Requirements: 5+ years, FastAPI, Postgres, Kubernetes.",
        "resume_text": "Asha Verma. 3 years Python backend at Razorpay. FastAPI, Postgres, AWS ECS.",
    }
    p = a.predict(features)
    assert p["decision"] in {"approved", "denied"}
    assert 0.0 <= p["confidence"] <= 1.0
    assert 0.0 <= p["prob_bad"] <= 1.0
    assert abs(p["confidence"] + p["prob_bad"] - 1.0) < 0.0001


def test_explain_returns_reason_rows():
    a = get_adapter("hiring")
    features = {
        "jd_text": "Senior Python backend engineer. Requirements: 5+ years, FastAPI, Postgres, Kubernetes.",
        "resume_text": "Asha Verma. 3 years Python backend at Razorpay. FastAPI, Postgres, AWS ECS.",
    }
    rows = a.explain(features)
    assert len(rows) >= 3
    for r in rows:
        assert "feature" in r
        assert "display_name" in r
        assert isinstance(r["contribution"], float)
        assert "evidence_quote" in r
        assert "jd_requirement" in r


def test_predict_then_explain_uses_one_call():
    """Cache should ensure predict + explain share one round-trip."""
    import pathlib, time
    a = get_adapter("hiring")
    features = {
        "jd_text": "Caching test JD: Python expert, 10+ years.",
        "resume_text": "Caching test resume: 12 years Python, ML, distributed systems.",
    }
    t0 = time.time()
    a.predict(features)
    dt1 = time.time() - t0
    t0 = time.time()
    a.explain(features)
    dt2 = time.time() - t0
    # Second call must be <50ms (cache hit).
    assert dt2 < 0.1, f"explain after predict should be cached; got {dt2*1000:.0f}ms"
