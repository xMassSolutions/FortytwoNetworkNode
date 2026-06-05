"""Shared cache. Backed by Redis when REDIS_URL is set -- so serverless
invocations share balance / node-name / login-rate-limit state instead of each
starting cold (which would hammer Monad RPC + the leaderboard and reset the
brute-force counter every request). Falls back to a process-local in-memory
dict when REDIS_URL is unset (Render / local dev), where behavior is identical
to the old per-cache dicts.

Callers store small JSON objects and do their own freshness check via a stored
`ts` field; the cache just persists the object (with a generous TTL for
cleanup), so the "serve the last-known value on a transient error" pattern keeps
working across invocations.
"""
import json
import os
import time
from typing import Any

REDIS_URL = os.environ.get("REDIS_URL", "").strip()
# Generous default so a key outlives its logical freshness window -- the app
# decides staleness from the stored `ts`; this is just garbage collection.
_DEFAULT_TTL = 7 * 24 * 3600

_redis: Any = None  # None = not tried; False = unavailable; else a client
_mem: dict[str, tuple[float, str]] = {}  # key -> (expires_at, json_str)


def _client() -> Any | None:
    global _redis
    if not REDIS_URL:
        return None
    if _redis is None:
        try:
            import redis  # lazy: only needed when REDIS_URL is set
            _redis = redis.from_url(
                REDIS_URL, decode_responses=True,
                socket_timeout=3, socket_connect_timeout=3,
            )
        except Exception:
            _redis = False  # missing package / bad URL -> use memory
    return _redis or None


def get_obj(key: str) -> Any | None:
    """Return the stored JSON object for `key`, or None."""
    r = _client()
    if r is not None:
        try:
            raw = r.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            pass  # Redis hiccup -> fall through to the in-memory mirror
    slot = _mem.get(key)
    if slot and slot[0] > time.time():
        try:
            return json.loads(slot[1])
        except Exception:
            return None
    return None


def set_obj(key: str, obj: Any, ttl: float | None = None) -> None:
    """Persist a JSON-serialisable object under `key`."""
    ttl = _DEFAULT_TTL if ttl is None else max(1.0, ttl)
    raw = json.dumps(obj, separators=(",", ":"), default=str)
    r = _client()
    if r is not None:
        try:
            r.setex(key, int(ttl), raw)
            return
        except Exception:
            pass
    _mem[key] = (time.time() + ttl, raw)


def delete(key: str) -> None:
    r = _client()
    if r is not None:
        try:
            r.delete(key)
            return
        except Exception:
            pass
    _mem.pop(key, None)
