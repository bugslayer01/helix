"""Disk-backed JSON cache for LLM calls.

Keyed by sha256(prompt+schema+model). Demo wifi can die; cached demo cases keep
working. Production uses Redis instead.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

_SAFE_KEY = re.compile(r"^[a-zA-Z0-9_\-]+$")


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
    """Look up ``key`` in ``cache_dir``; on miss, call ``fn`` and persist.

    The key must match ``[a-zA-Z0-9_-]+``. This rejects path-traversal
    sequences (``..``, ``/``) and empty keys up-front — every current caller
    passes a sha256 hex string, but this guards future misuse.
    """
    if not _SAFE_KEY.match(key):
        raise ValueError(f"cache key must match [a-zA-Z0-9_-]+; got {key!r}")
    f = cache_dir / f"{key}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            f.unlink(missing_ok=True)
    result = fn()
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result, indent=2))
    os.replace(tmp, f)
    return result
