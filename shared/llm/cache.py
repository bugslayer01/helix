"""Disk-backed JSON cache for LLM calls.

Keyed by sha256(prompt+schema+model). Demo wifi can die; cached demo cases keep
working. Production uses Redis instead.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable


def make_key(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def disk_cache_for(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    return root


def cached_call(cache_dir: Path, key: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    f = cache_dir / f"{key}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            f.unlink(missing_ok=True)
    result = fn()
    f.write_text(json.dumps(result, indent=2))
    return result
