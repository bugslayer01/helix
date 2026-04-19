from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DomainAdapter(Protocol):
    """Recourse Model Protocol — every domain implements this contract.

    The frontend renders no domain-specific copy of its own; everything comes
    back from these methods. Adding a new adapter file + registering it is the
    only work needed to ship a new domain.
    """

    # --- identity ---------------------------------------------------------
    domain_id: str
    display_name: str
    model_version_hash: str

    # --- prediction + explanation ----------------------------------------

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """Return {decision: 'approved'|'denied', confidence: 0..1, prob_bad: 0..1}.

        `confidence` is ALWAYS the probability of the approved class so the
        frontend can tween a single monotonic number across a contest.
        """
        ...

    def explain(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        """Return SHAP-style attribution, one dict per feature. Positive
        contribution means "pushed toward the approved class"."""
        ...

    def feature_schema(self) -> list[dict[str, Any]]:
        """Metadata for every feature — ordering/groups, contestable flag,
        protected flag, evidence types, realistic bounds, UI hint text."""
        ...

    def suggest_counterfactual(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        """Offline-precomputed hints. May return [] if unsupported."""
        ...

    # --- UI-driving metadata ---------------------------------------------

    def verbs(self) -> dict[str, str]:
        """Every human-readable token the frontend needs for this domain.

        Keys:
          subject_noun, approved_label, denied_label,
          hero_question, hero_subtitle,
          outcome_title_flipped, outcome_title_same, outcome_review_title,
          correction_title, new_evidence_title, review_title,
          correction_button, review_button
        """
        ...

    def profile_groups(self) -> list[dict[str, Any]]:
        """Ordered list of {id, title, field_keys, locked, locked_hint?}.

        `field_keys` references `feature_schema()` entries by their `feature`.
        """
        ...

    def path_reasons(self) -> dict[str, list[dict[str, str]]]:
        """Reason dropdowns per path.

        Shape: {contest: [{value, label}], review: [{value, label}]}.
        """
        ...

    def legal_citations(self) -> list[str]:
        """Jurisdictional hooks ("GDPR Art. 22(3)", ...) for the review path."""
        ...

    # --- evidence / extraction seams (domain expansion) ------------------

    def intake_doc_types(self) -> list[dict[str, Any]]:
        """Document types accepted at application time (customer portal).

        Each entry: {id, display_name, accepted_mime, required, freshness_days}.
        """
        ...

    def evidence_doc_types(self, target_feature: str) -> list[dict[str, Any]]:
        """Document types accepted during contest to change a given feature.

        Same shape as ``intake_doc_types`` plus ``extracts_feature``.
        """
        ...

    def extract_prompt(self, doc_type: str) -> dict[str, Any]:
        """Prompt + JSON schema for GLM-OCR for this doc_type.

        Returns {prompt: str, schema: dict, feature_field: str|None}. The
        ``feature_field`` tells the pipeline which extracted key is the
        numeric value to plug into the feature vector for re-evaluation.
        """
        ...
