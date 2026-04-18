from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from adapters import get_adapter, list_domains
from seed_cases import SEED_CASES, cases_by_domain, find_case
from services import audit_log

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


class LookupRequest(BaseModel):
    application_reference: str
    date_of_birth: str


class EvaluateRequest(BaseModel):
    domain: str
    applicant_id: str | None = None
    features: dict


def _build_evaluation(case_id: str, domain: str, features: dict, applicant_name: str | None = None) -> dict:
    adapter = get_adapter(domain)
    explain_features = {**features, "_case_id": case_id}
    prediction = adapter.predict(features)
    shap_values = adapter.explain(explain_features)
    hints = adapter.suggest_counterfactual(explain_features)

    return {
        "case_id": case_id,
        "domain": domain,
        "display_name": adapter.display_name,
        "decision": prediction["decision"],
        "confidence": prediction["confidence"],
        "model_version_hash": adapter.model_version_hash,
        "shap_values": shap_values,
        "feature_values": features,
        "plain_language_reason": _plain_language_reason(shap_values, prediction["decision"], adapter),
        "suggested_evidence": hints,
        "verbs": adapter.verbs(),
        "profile_groups": adapter.profile_groups(),
        "feature_schema": adapter.feature_schema(),
        "path_reasons": adapter.path_reasons(),
        "legal_citations": adapter.legal_citations(),
        "applicant_name": applicant_name,
    }


def _plain_language_reason(shap_values: list[dict], decision: str, adapter) -> str:
    if not shap_values:
        return "The model weighed several signals before producing this decision."
    sorted_rows = sorted(
        (r for r in shap_values if not r.get("protected")),
        key=lambda r: abs(r["contribution"]),
        reverse=True,
    )
    if not sorted_rows:
        return "The model weighed several signals before producing this decision."
    top = sorted_rows[0]
    verbs = adapter.verbs()
    direction = "primary factor" if decision == "denied" else "strongest supporting factor"
    subject = verbs.get("subject_noun", "case")
    return (
        f"The model's {direction} in your {subject} was "
        f"{top['display_name'].lower()}. "
        f"It weighed this signal heavily relative to the others."
    )


@router.post("/lookup")
def lookup(req: LookupRequest) -> dict:
    case = find_case(req.application_reference, req.date_of_birth)
    if not case:
        raise HTTPException(
            status_code=404,
            detail="No application matches this reference and date of birth.",
        )
    result = _build_evaluation(
        case["case_id"],
        case["domain"],
        case["features"],
        applicant_name=case.get("applicant_name"),
    )
    audit_log.append(
        case_id=case["case_id"],
        action="sign_in",
        title="Signed in",
        subtitle="reference + DOB verified",
        payload={"reference": req.application_reference},
    )
    return result


@router.post("")
def evaluate(req: EvaluateRequest) -> dict:
    if req.applicant_id is None:
        raise HTTPException(status_code=400, detail="applicant_id required for direct evaluate")
    return _build_evaluation(req.applicant_id, req.domain, req.features)


@router.get("/domains")
def domains() -> dict:
    grouped = cases_by_domain()
    return {
        "domains": list_domains(),
        "cases_by_domain": {
            domain: [
                {
                    "case_id": c["case_id"],
                    "applicant_reference": c["application_reference"],
                    "applicant_name": c.get("applicant_name"),
                    "date_of_birth": c["date_of_birth"],
                }
                for c in cases
            ]
            for domain, cases in grouped.items()
        },
    }
