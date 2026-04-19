"""Shared helpers for DomainAdapter implementations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    if not path.exists():
        return "sha256:pending"
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def identity_sha256(identity: str) -> str:
    """Stable hash for adapters that don't have a .pkl artifact (rule-based)."""
    return f"sha256:{hashlib.sha256(identity.encode()).hexdigest()}"


def load_json(path: Path, default: Any) -> Any:
    try:
        with path.open() as f:
            return json.load(f)
    except FileNotFoundError:
        return default


UNIVERSAL_REVIEW_REASONS = [
    {
        "value": "protected_attribute_bias",
        "label": "A protected attribute seems to have influenced the decision",
    },
    {
        "value": "inappropriate_use_of_model",
        "label": "The model shouldn't have been used for my situation",
    },
    {
        "value": "model_misweighted_correct_data",
        "label": "My data is correct, but the model weighted it unfairly",
    },
    {"value": "other", "label": "Other"},
]


UNIVERSAL_CONTEST_REASONS = [
    {"value": "stale_data", "label": "Stale data (was correct once, not anymore)"},
    {"value": "data_entry_error", "label": "Data entry error"},
    {"value": "circumstances_changed", "label": "Circumstances changed"},
    {"value": "missing_information", "label": "Missing information"},
    {"value": "protected_attribute", "label": "Concern about a protected attribute"},
    {"value": "other", "label": "Other"},
]
