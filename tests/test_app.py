"""Server power summary: the configurable whole-rig overhead is added to the
live kW, and overhead alone is not shown when the GPU reports no power."""
import time

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
