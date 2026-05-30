"""Chain-scan resilience: a block range skipped on an RPC give-up is queued and
recovered on a later refresh (instead of being lost forever)."""
import asyncio

import rewards
from rewards import RewardsTracker

# Use the real UTC day so refresh() doesn't trigger a day-rollover that would
# wipe pending_rescan mid-test.
DAY = rewards._utc_today_str()
MID = rewards._utc_midnight_ts()


def test_rescan_recovers_previously_skipped_range(monkeypatch):
    t = RewardsTracker(wallet="0xabc")
    t.today_utc_date = DAY
    t.today_midnight_ts = MID
    t.today_midnight_block = 50
    t.last_scanned_block = 200        # caught up -> only the rescan drain runs
    t._historical_loaded = True       # skip the DB load
    t.last_refresh_ts = 0             # past the TTL guard
    t.pending_rescan = [(100, 104)]   # a range we gave up on earlier

    async def fake_latest(_rpc):
        return 200

    async def fake_transfers(_rpc, _contract, _tos, lo, _hi):
        if lo == 100:  # the skipped range now succeeds
            return [{"amount": 5.0, "tx_hash": "0xT", "block_number": 102, "log_index": 0}]
        return []

    async def fake_blockts(_rpc, _bn):
        return MID + 3600  # 01:00 today

    monkeypatch.setattr(rewards, "get_latest_block", fake_latest)
    monkeypatch.setattr(rewards, "get_transfer_events", fake_transfers)
    monkeypatch.setattr(rewards, "get_block_timestamp", fake_blockts)

    asyncio.run(t.refresh("rpc", "0xFOR"))

    assert [x.tx_hash for x in t.today_transfers] == ["0xT"]
    assert t.pending_rescan == []


def test_rescan_keeps_range_that_still_fails(monkeypatch):
    t = RewardsTracker(wallet="0xabc")
    t.today_utc_date = DAY
    t.today_midnight_ts = MID
    t.today_midnight_block = 50
    t.last_scanned_block = 200
    t._historical_loaded = True
    t.last_refresh_ts = 0
    t.pending_rescan = [(100, 104)]

    async def fake_latest(_rpc):
        return 200

    async def still_413(_rpc, _contract, _tos, _lo, _hi):
        raise RuntimeError("413 Request Entity Too Large")

    monkeypatch.setattr(rewards, "get_latest_block", fake_latest)
    monkeypatch.setattr(rewards, "get_transfer_events", still_413)

    asyncio.run(t.refresh("rpc", "0xFOR"))

    # still failing -> stays queued for next time, nothing lost
    assert t.pending_rescan == [(100, 104)]
    assert t.today_transfers == []
