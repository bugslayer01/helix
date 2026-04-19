"""Adapter contract tests — pure-Python (no live LLM calls)."""
from shared.adapters import get_adapter


def test_hiring_adapter_registered():
    a = get_adapter("hiring")
    assert a.domain_id == "hiring"
    assert a.display_name


def test_intake_doc_types_present():
    a = get_adapter("hiring")
    docs = a.intake_doc_types()
    ids = {d["id"] for d in docs}
    assert "resume" in ids
    assert "job_description" in ids
    for d in docs:
        assert {"id", "display_name", "accepted_mime", "required", "freshness_days"} <= set(d)


def test_evidence_doc_types_for_any_reason():
    a = get_adapter("hiring")
    docs = a.evidence_doc_types("missing_skill")
    ids = {d["id"] for d in docs}
    assert "certificate" in ids
    assert "course_completion" in ids
    assert "resume" in ids


def test_extract_prompt_for_resume_doc():
    a = get_adapter("hiring")
    p = a.extract_prompt("resume")
    assert "schema" in p
    assert p["schema"]["type"] == "object"
    assert "doc_type" in p["schema"]["properties"]


def test_model_version_starts_with_sha256():
    a = get_adapter("hiring")
    assert a.model_version_hash.startswith("sha256:")


def test_verbs_has_required_keys():
    a = get_adapter("hiring")
    v = a.verbs()
    for k in ("subject_noun", "approved_label", "denied_label", "hero_question", "correction_title"):
        assert k in v


def test_feature_schema_has_resume_text_slot():
    a = get_adapter("hiring")
    schema = a.feature_schema()
    assert any(s["feature"] == "resume_text" for s in schema)
