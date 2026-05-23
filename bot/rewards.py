"""On-chain reward tracker — sums ERC-20 Transfer events into the operator
wallet since 00:00 UTC today.

The agent's log-derived `rewards_today_total` only captures rewards the Capsule
log emits a `FOR balance before/after reward` pair for, which structurally
undercounts (observer rewards, periodic distributions land on-chain but never in
the log). This tracker is the authoritative number for the dashboard's
"FOR earned today" headline.

Design:
- Singleton `tracker` instance. Refresh is idempotent + cached (30s TTL,
  matching `_cached_balance`).
- First call after a fresh deploy: find the block whose timestamp >= today's
  UTC midnight via binary search (~20 RPC calls). Then scan from there to
  `latest` in chunks of <=1000 blocks via `get_transfer_events`.
- Subsequent calls: scan from `last_scanned_block + 1` to `latest` (usually
  <30 blocks → 1 RPC call).
- UTC day rollover: clear today_transfers, re-find midnight block on next
  refresh.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from chain import (
    get_block_timestamp,
    get_latest_block,
    get_transfer_events,
)

_TTL_SECONDS = 30.0
_CHUNK_SIZE = 1000  # eth_getLogs block-range cap per request


def _utc_today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _utc_midnight_ts() -> int:
    """Unix timestamp at 00:00:00 UTC today."""
    now = datetime.now(timezone.utc)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(midnight.timestamp())


@dataclass
class _Transfer:
    amount: float
    tx_hash: str
    block_number: int
    log_index: int
    ts: int  # block timestamp, unix seconds UTC

    @property
    def iso(self) -> str:
        return datetime.fromtimestamp(self.ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class RewardsTracker:
    today_utc_date: str | None = None
    today_midnight_ts: int | None = None
    today_midnight_block: int | None = None
    today_transfers: list[_Transfer] = field(default_factory=list)
    last_scanned_block: int | None = None
    last_refresh_ts: float = 0.0
    last_error: str | None = None

    def _reset_for_new_day(self) -> None:
        self.today_utc_date = _utc_today_str()
        self.today_midnight_ts = _utc_midnight_ts()
        self.today_midnight_block = None
        self.today_transfers = []
        self.last_scanned_block = None

    async def _find_midnight_block(self, rpc_url: str) -> int:
        """Binary-search the first block whose timestamp >= today's UTC midnight.

        Bounds:
          high = latest block
          low  = high - ceil(seconds_since_midnight / min_block_seconds) * safety
        Falls back to scanning the last 200k blocks if estimation fails.
        """
        assert self.today_midnight_ts is not None
        target = self.today_midnight_ts

        latest = await get_latest_block(rpc_url)
        latest_ts = await get_block_timestamp(rpc_url, latest)
        if latest_ts <= target:
            # Edge: midnight hasn't started producing blocks yet. Use latest.
            return latest

        # Monad testnet blocks are ~1s; over-estimate to 0.5s for safety.
        elapsed = max(1, latest_ts - target)
        est_blocks = int(elapsed / 0.5) + 100
        low = max(0, latest - est_blocks)

        # If our estimated low isn't actually before midnight, widen until it is.
        for _ in range(5):
            low_ts = await get_block_timestamp(rpc_url, low)
            if low_ts < target:
                break
            low = max(0, low - est_blocks)
            if low == 0:
                break
        high = latest

        # Binary search: first block with ts >= target.
        while low < high:
            mid = (low + high) // 2
            ts = await get_block_timestamp(rpc_url, mid)
            if ts < target:
                low = mid + 1
            else:
                high = mid
        return low

    async def refresh(self, rpc_url: str, for_contract: str, wallet: str) -> None:
        now = time.time()
        today = _utc_today_str()

        # Day rollover
        if today != self.today_utc_date:
            self._reset_for_new_day()

        # TTL — don't hammer RPC
        if now - self.last_refresh_ts < _TTL_SECONDS and self.today_midnight_block is not None:
            return

        try:
            if self.today_midnight_block is None:
                self.today_midnight_block = await self._find_midnight_block(rpc_url)
                self.last_scanned_block = self.today_midnight_block - 1

            latest = await get_latest_block(rpc_url)
            assert self.last_scanned_block is not None
            from_block = self.last_scanned_block + 1
            if from_block > latest:
                self.last_refresh_ts = now
                self.last_error = None
                return

            # Chunk to respect eth_getLogs range limits.
            cursor = from_block
            while cursor <= latest:
                chunk_end = min(cursor + _CHUNK_SIZE - 1, latest)
                events = await get_transfer_events(
                    rpc_url, for_contract, [wallet], cursor, chunk_end
                )
                # Annotate with block timestamp (one extra RPC per unique block).
                seen_block_ts: dict[int, int] = {}
                for ev in events:
                    bn = ev["block_number"]
                    if bn not in seen_block_ts:
                        seen_block_ts[bn] = await get_block_timestamp(rpc_url, bn)
                    ts = seen_block_ts[bn]
                    # Defensive: only include if >= midnight (block at boundary).
                    if ts < (self.today_midnight_ts or 0):
                        continue
                    self.today_transfers.append(
                        _Transfer(
                            amount=ev["amount"],
                            tx_hash=ev["tx_hash"],
                            block_number=bn,
                            log_index=ev["log_index"],
                            ts=ts,
                        )
                    )
                self.last_scanned_block = chunk_end
                cursor = chunk_end + 1

            # Sort by (block, log_index) so summary() last-item is genuinely latest.
            self.today_transfers.sort(key=lambda t: (t.block_number, t.log_index))
            self.last_refresh_ts = now
            self.last_error = None
        except Exception as e:
            # Keep last-known good state; surface error so dashboard can show it
            # rather than blanking the card.
            self.last_error = f"{type(e).__name__}: {e}"

    def summary(self) -> dict[str, Any]:
        earned = sum(t.amount for t in self.today_transfers)
        count = len(self.today_transfers)
        last = self.today_transfers[-1] if self.today_transfers else None
        return {
            "earned_today": round(earned, 6) if earned else 0.0,
            "transfers_today": count,
            "last_transfer_amount": round(last.amount, 6) if last else None,
            "last_transfer_iso": last.iso if last else None,
            "last_transfer_tx": last.tx_hash if last else None,
            "refreshed_at": self.last_refresh_ts or None,
            "error": self.last_error,
        }


tracker = RewardsTracker()
