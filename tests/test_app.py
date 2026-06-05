"""Server power summary + mandatory-auth boot check: the configurable whole-rig
overhead is added to the live kW (and overhead alone isn't shown when the GPU
reports no power), and the app refuses to boot without dashboard credentials."""
import time

import pytest

import app
from store import Snapshot, store


def test_power_overhead_added_to_current_kw(monkeypatch, fresh_db):
    monkeypatch.setattr(app, "POWER_OVERHEAD_WATTS", 100.0)
    store.set(Snapshot(received_at=time.time(), ts="2026-05-29T10:00:00Z",
                       node_id=1, gpu_power_w=400.0))
    assert app._power_summary(1)["current_kw"] == 0.5   # (400 + 100) / 1000


def test_no_power_shown_without_gpu_reading(monkeypatch, fresh_db):
    monkeypatch.setattr(app, "POWER_OVERHEAD_WATTS", 100.0)
    store.set(Snapshot(received_at=time.time(), ts="2026-05-29T10:00:00Z",
                       node_id=2, gpu_power_w=None))
    # overhead-only must NOT manufacture a kW reading on a non-reporting node
    assert app._power_summary(2)["current_kw"] is None


def test_require_auth_configured_raises_without_creds(monkeypatch):
    # Mandatory login: the server must refuse to boot when creds are unset.
    monkeypatch.setattr(app, "AUTH_ENABLED", False)
    with pytest.raises(RuntimeError, match="mandatory"):
        app._require_auth_configured()


def test_require_auth_configured_ok_with_creds(monkeypatch):
    monkeypatch.setattr(app, "AUTH_ENABLED", True)
    app._require_auth_configured()  # configured -> no raise


def test_sample_uptime_once_writes_a_row(fresh_db):
    # The extracted cron-callable samples uptime for every known node.
    store.set(Snapshot(received_at=time.time(), node_id=3,
                       node_wallet="0x" + "c" * 40, gpu_power_w=200.0))
    app.sample_uptime_once()
    rows = fresh_db.load_uptime_samples_since(3, 0)
    assert len(rows) >= 1


class _Req:  # minimal Request stub for the cron-auth check
    def __init__(self, auth: str | None):
        self.headers = {"authorization": auth} if auth else {}


def test_cron_auth_rejects_unconfigured_and_wrong_secret(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setattr(app, "CRON_SECRET", "")          # not configured
    with pytest.raises(HTTPException) as e:
        app._require_cron_auth(_Req("Bearer x"))
    assert e.value.status_code == 503
    monkeypatch.setattr(app, "CRON_SECRET", "s3cr3t")    # wrong token
    with pytest.raises(HTTPException) as e:
        app._require_cron_auth(_Req("Bearer nope"))
    assert e.value.status_code == 401
    app._require_cron_auth(_Req("Bearer s3cr3t"))         # correct -> no raise
