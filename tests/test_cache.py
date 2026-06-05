"""Shared cache shim -- the in-memory fallback path (Render / local, no
REDIS_URL) round-trips JSON objects and honors TTL expiry. The Redis path is a
thin redis-py wrapper exercised when REDIS_URL is set on the deploy host."""
import time

import cache


def _mem_only(monkeypatch):
    monkeypatch.setattr(cache, "REDIS_URL", "")  # force the in-memory backend
    cache._mem.clear()


def test_set_get_roundtrip(monkeypatch):
    _mem_only(monkeypatch)
    cache.set_obj("k", {"a": 1, "ts": 9})
    assert cache.get_obj("k") == {"a": 1, "ts": 9}


def test_missing_key_is_none(monkeypatch):
    _mem_only(monkeypatch)
    assert cache.get_obj("nope") is None


def test_ttl_expiry(monkeypatch):
    _mem_only(monkeypatch)
    cache.set_obj("k", {"v": 1}, ttl=60)
    assert cache.get_obj("k") == {"v": 1}
    # force the stored expiry into the past
    cache._mem["k"] = (time.time() - 1, cache._mem["k"][1])
    assert cache.get_obj("k") is None


def test_delete(monkeypatch):
    _mem_only(monkeypatch)
    cache.set_obj("k", {"v": 1})
    cache.delete("k")
    assert cache.get_obj("k") is None


def test_list_value_for_rate_limit(monkeypatch):
    # the login rate-limit stores a list of timestamps under one key
    _mem_only(monkeypatch)
    cache.set_obj("login:1.2.3.4", [100.0, 101.0])
    assert cache.get_obj("login:1.2.3.4") == [100.0, 101.0]
