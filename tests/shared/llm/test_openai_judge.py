import json
from pathlib import Path
import pytest
from shared.llm.cache import disk_cache_for, cached_call


def test_cache_miss_calls_fn(tmp_path: Path):
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        return {"x": 1}
    out = cached_call(disk_cache_for(tmp_path), "k1", fn)
    assert out == {"x": 1}
    assert calls["n"] == 1


def test_cache_hit_skips_fn(tmp_path: Path):
    calls = {"n": 0}
    def fn():
        calls["n"] += 1
        return {"x": 1}
    cached_call(disk_cache_for(tmp_path), "k1", fn)
    cached_call(disk_cache_for(tmp_path), "k1", fn)
    assert calls["n"] == 1


def test_cache_different_keys_isolated(tmp_path: Path):
    out1 = cached_call(disk_cache_for(tmp_path), "k1", lambda: {"a": 1})
    out2 = cached_call(disk_cache_for(tmp_path), "k2", lambda: {"a": 2})
    assert out1["a"] == 1
    assert out2["a"] == 2
