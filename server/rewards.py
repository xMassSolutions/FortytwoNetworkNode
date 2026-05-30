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

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from chain import (
    get_block_timestamp,
    get_latest_block,
    get_transfer_events,
)
from db import load_daily_totals, upsert_daily_total

_TTL_SECONDS = 30.0
# Monad's public testnet RPC (https://testnet-rpc.monad.xyz/) returns
# `413 Request Entity Too Large` on eth_getLogs over wide ranges. 100 blocks
# is the safe upper bound we've observed. If you point MONAD_RPC_URL at a paid
# provider (Alchemy, BlockVision, etc.) you can bump this without code changes.
# Relaxed-pass forward window for tx<->round matching (env-tunable). Rewards
# that resolve later than this stay unmatched. Default 30 min.
_RELAXED_PAD_SECONDS = max(60, int(os.environ.get("MATCH_RELAXED_MINUTES", "30")) * 60)
# Cap on block ranges queued for re-scan after an RPC give-up (bounded memory).
_MAX_PENDING_RESCAN = 50
_CHUNK_SIZE = 100
_MIN_CHUNK_SIZE = 5  # halving floor on retry — below this we skip the chunk
# Per-request cap when fanning out blockNumber → timestamp lookups
_MAX_BLOCK_TS_LOOKUPS_PER_CHUNK = 50


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
    # Lowercased operator wallet this tracker is scanning. One tracker per
    # wallet — see `get_tracker()` at module bottom. Required field.
    wallet: str = ""
    today_utc_date: str | None = None
    today_midnight_ts: int | None = None
    today_midnight_block: int | None = None
    today_transfers: list[_Transfer] = field(default_factory=list)
    # Yesterday's transfers — preserved across UTC-midnight rollover so the
    # 24h rounds chart's earlier bars (which span yesterday's hours) can
    # show real FOR/hour in their tooltips instead of "—".
    yesterday_transfers: list[_Transfer] = field(default_factory=list)
    yesterday_utc_date: str | None = None
    # Historical per-hour totals loaded from SQLite on startup. Keyed
    # "YYYY-MM-DDTHH" so it stacks cleanly into transfers_by_hour without
    # collisions. Survives container restarts inside a single deploy;
    # NOT Render redeploys (filesystem is ephemeral on free tier).
    historical_by_hour: dict[str, float] = field(default_factory=dict)
    last_scanned_block: int | None = None
    last_refresh_ts: float = 0.0
    last_error: str | None = None
    # Block ranges [(lo, hi)] skipped on RPC give-up, retried on later refreshes
    # so their transfers (and earnings) aren't lost permanently.
    pending_rescan: list = field(default_factory=list)
    _historical_loaded: bool = False  # one-shot guard for lazy load

    def _ensure_historical_loaded(self) -> None:
        """Load daily_totals rows from SQLite into self.historical_by_hour.
        Called lazily on first refresh so we don't crash if db.py isn't
        importable (e.g. during tests that stub the chain module)."""
        if self._historical_loaded:
            return
        try:
            for row in load_daily_totals(self.wallet):
                for k, v in (row.get("by_hour") or {}).items():
                    try:
                        self.historical_by_hour[k] = float(v)
                    except (TypeError, ValueError):
                        continue
        except Exception:
            pass  # SQLite unavailable / empty — non-fatal
        self._historical_loaded = True

    def _persist_today(self) -> None:
        """Upsert today's current state into the daily_totals table."""
        if not self.today_utc_date:
            return
        by_hour: dict[str, float] = {}
        for t in self.today_transfers:
            dt = datetime.fromtimestamp(t.ts, tz=timezone.utc)
            key = dt.strftime("%Y-%m-%dT%H")
            by_hour[key] = by_hour.get(key, 0.0) + t.amount
        try:
            upsert_daily_total(
                self.today_utc_date,
                self.wallet,
                {k: round(v, 6) for k, v in by_hour.items()},
                round(sum(t.amount for t in self.today_transfers), 6),
                len(self.today_transfers),
                time.time(),
            )
            # Also fold today's keys into historical_by_hour so subsequent
            # summary() calls see the latest without re-reading SQLite.
            for k, v in by_hour.items():
                self.historical_by_hour[k] = round(v, 6)
        except Exception:
            pass  # non-fatal

    def _reset_for_new_day(self) -> None:
        # Persist the day we're leaving BEFORE clearing in-memory state, so
        # we never lose a finished day to a poorly-timed redeploy.
        if self.today_transfers and self.today_utc_date:
            self._persist_today()
            self.yesterday_transfers = self.today_transfers
            self.yesterday_utc_date = self.today_utc_date
        self.today_utc_date = _utc_today_str()
        self.today_midnight_ts = _utc_midnight_ts()
        self.today_midnight_block = None
        self.today_transfers = []
        self.last_scanned_block = None
        self.pending_rescan = []

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

    async def _fetch_chunk_with_halving(
        self, rpc_url: str, for_contract: str,
        cursor: int, chunk_end: int,
    ) -> tuple[list[dict], int, str | None]:
        """Try eth_getLogs over [cursor, chunk_end]. On 413 or timeout, halve
        the range and retry, down to `_MIN_CHUNK_SIZE`. Returns
        (events, last_block_actually_scanned, error_or_None).
        """
        attempt_end = chunk_end
        last_err: str | None = None
        while attempt_end >= cursor:
            try:
                events = await get_transfer_events(
                    rpc_url, for_contract, [self.wallet], cursor, attempt_end
                )
                return events, attempt_end, None
            except Exception as e:
                msg = str(e)
                last_err = f"{type(e).__name__}: {msg}"
                # Halve only on size-related errors and timeouts; bail on other errors.
                # httpx.TimeoutException covers Connect/Read/Write/PoolTimeout (the
                # actual client below is httpx via chain.rpc_call). The substring
                # check is a defensive net for wrapped/upstream errors whose message
                # mentions timeout but whose type we can't predict.
                is_timeout = isinstance(e, httpx.TimeoutException) or "timeout" in msg.lower()
                if not is_timeout and "413" not in msg and "Too Large" not in msg:
                    return [], cursor - 1, last_err
                span = attempt_end - cursor + 1
                if span <= _MIN_CHUNK_SIZE:
                    # Give up on this chunk; skip past it so we make progress next refresh.
                    return [], attempt_end, last_err
                attempt_end = cursor + (span // 2) - 1
        return [], cursor - 1, last_err

    async def _ingest_events(self, rpc_url: str, events: list[dict]) -> None:
        """Annotate raw transfer events with block timestamps and append today's
        to self.today_transfers. Block-ts lookups are capped per call; over the
        cap (or on lookup failure) we approximate from the last resolved ts -- a
        near lower-bound since events arrive ascending by (block, logIndex)."""
        seen_block_ts: dict[int, int] = {}
        ts_lookups = 0
        last_real_ts = self.today_midnight_ts or 0
        for ev in events:
            bn = ev["block_number"]
            if bn not in seen_block_ts:
                if ts_lookups >= _MAX_BLOCK_TS_LOOKUPS_PER_CHUNK:
                    seen_block_ts[bn] = last_real_ts
                else:
                    try:
                        real = await get_block_timestamp(rpc_url, bn)
                        seen_block_ts[bn] = real
                        last_real_ts = real
                        ts_lookups += 1
                    except Exception:
                        seen_block_ts[bn] = last_real_ts
            ts = seen_block_ts[bn]
            if ts < (self.today_midnight_ts or 0):
                continue
            self.today_transfers.append(
                _Transfer(amount=ev["amount"], tx_hash=ev["tx_hash"],
                          block_number=bn, log_index=ev["log_index"], ts=ts))

    async def refresh(self, rpc_url: str, for_contract: str) -> None:
        now = time.time()
        today = _utc_today_str()

        # Lazy-load persisted daily_totals on first refresh.
        self._ensure_historical_loaded()

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

            # Retry ranges we previously skipped on an RPC give-up; recovered
            # transfers fill back in, ranges that still fail stay queued. Runs
            # even when caught up (no new blocks) so retries aren't starved.
            if self.pending_rescan:
                still: list = []
                for lo, hi in self.pending_rescan:
                    ev2, _adv, err2 = await self._fetch_chunk_with_halving(
                        rpc_url, for_contract, lo, hi)
                    if ev2:
                        await self._ingest_events(rpc_url, ev2)
                    elif err2:
                        still.append((lo, hi))
                self.pending_rescan = still

            if from_block > latest:
                self.last_refresh_ts = now
                self.last_error = None
                # Recovered rescan transfers (if any) need re-sorting here since
                # we skip the post-loop sort below.
                self.today_transfers.sort(key=lambda t: (t.block_number, t.log_index))
                return

            # Chunk to respect eth_getLogs range limits. Each successful chunk
            # advances `last_scanned_block` so partial progress sticks across
            # refreshes — a 413 on the 5th chunk doesn't lose the first 4.
            chunk_err: str | None = None
            cursor = from_block
            while cursor <= latest:
                chunk_end = min(cursor + _CHUNK_SIZE - 1, latest)
                events, advanced_to, err = await self._fetch_chunk_with_halving(
                    rpc_url, for_contract, cursor, chunk_end,
                )
                if err and not events:
                    chunk_err = err
                    if advanced_to >= cursor:
                        # Gave up on this range -- skip past it for forward
                        # progress, but queue it for a later re-scan so its
                        # transfers (and earnings) aren't lost for good.
                        self.pending_rescan.append((cursor, advanced_to))
                        if len(self.pending_rescan) > _MAX_PENDING_RESCAN:
                            self.pending_rescan = self.pending_rescan[-_MAX_PENDING_RESCAN:]
                        self.last_scanned_block = advanced_to
                        cursor = advanced_to + 1
                        continue
                    # Couldn't make progress at all -> bail out for this refresh.
                    break

                await self._ingest_events(rpc_url, events)
                self.last_scanned_block = advanced_to
                cursor = advanced_to + 1

            # Sort by (block, log_index) so summary() last-item is genuinely latest.
            self.today_transfers.sort(key=lambda t: (t.block_number, t.log_index))
            self.last_refresh_ts = now
            # Partial-success semantics: clear last_error if we made progress
            # (transfers got appended); keep error context if we made none.
            self.last_error = chunk_err if (chunk_err and not self.today_transfers) else None
            # Persist today's state to SQLite so a container restart inside
            # this deploy doesn't lose the data. (Render redeploys still
            # wipe the SQLite file — see db.py header.)
            self._persist_today()
        except Exception as e:
            # Keep last-known good state; surface error so dashboard can show it
            # rather than blanking the card.
            self.last_error = f"{type(e).__name__}: {e}"

    def attach_tx_hashes(
        self,
        rounds: list[dict[str, Any]],
        today_date: str | None,
        pad_seconds: int = 300,
    ) -> list[dict[str, Any]]:
        """Inject `tx_hash` into round dicts whose tx_hash is null/missing,
        sourcing from `self.today_transfers` by interval-overlap match.

        Why: recent Capsule versions stopped logging `Resolution of ...
        receipt hash 0x...` so the agent's parser can't pair tx hashes.
        Chain-side matching is format-independent and uses the authoritative
        Monad receipt.

        Completion-anchored matching:
          Rewards land on-chain AFTER a round completes (the Capsule submits
          intent resolution post-completion), so each round's match window is
          anchored at its completion time and is ASYMMETRIC: it reaches only a
          small clock-skew slack backward but the full deferred-resolution
          allowance forward. A transfer is a candidate iff its ts is in
          `[completed_ts - back_pad, completed_ts + fwd_pad]`. Among candidates,
          transfers at/after completion are preferred over earlier ones (the
          only reason to look before completion is workstation/chain clock
          skew), then by closeness to completion. Greedy in completion order so
          earlier rounds claim first; the `used` set stops one transfer being
          claimed twice. Two passes:
            1. STRICT  back=fwd=`pad_seconds` (default ±5 min).
            2. RELAXED extend FORWARD only to `pad_seconds * 6` (default 30 min)
               for deferred-resolution rounds (the Capsule logs `Waiting for N
               milliseconds before resolving intent`, observed >5 min in the
               wild); backward stays at `pad_seconds`. Widening backward to
               30 min is exactly how a later round used to claim an earlier
               round's transfer -- a transfer that landed minutes before a
               round completed can't be that round's reward.
            3. GAP-FILL for anything still unmatched: a reward often only
               lands on-chain by the time the NEXT round begins (past the
               relaxed window, or after the last scan for the most recent
               round). In completion order, claim the earliest unused
               transfer in the gap `[this completion, next completion)` —
               open-ended for the most recent round. Additive: never
               re-claims a transfer or round already matched above.
          Earlier versions (v10.1) anchored on the round midpoint and extended
          the window backward by the full round duration. With long durations
          and concurrent rounds that let an earlier round reach back and steal
          a later round's transfer, leaving the later round showing `—`.
        Risk acknowledged: this is still a time-only match, so when on-chain
        resolution order differs from completion order it can mis-attribute.
        Since observer rounds are skipped (`participated: False`) and `used`
        prevents double-claims, the worst case is "tx_hash points at a nearby
        wallet credit rather than this exact round" — verifiable on monadscan;
        showing `—` for half the participations is worse UX.

        Returns a NEW list (doesn't mutate input). Rounds with a non-null
        tx_hash already populated by the agent are left untouched.

        Pre-conditions: `today_date` is a "YYYY-MM-DD" string used to convert
        each round's `completed_iso` (HH:MM:SS) to a UTC epoch.
        """
        if not rounds or not self.today_transfers or not today_date:
            return rounds
        try:
            midnight = datetime.fromisoformat(today_date).replace(tzinfo=timezone.utc)
            midnight_ts = int(midnight.timestamp())
        except Exception:
            return rounds

        # Exclude any tx_hash that's already claimed by a round (e.g., the
        # agent attached it via the legacy "receipt hash 0x..." log line).
        # Without this, the matcher would re-attach the same tx to a second
        # round that happens to have an overlapping interval window.
        already_claimed: set[str] = {r["tx_hash"] for r in rounds if r.get("tx_hash")}
        avail: list[tuple[int, str, float]] = sorted(
            [(t.ts, t.tx_hash, t.amount) for t in self.today_transfers
             if t.tx_hash not in already_claimed],
            key=lambda x: x[0],
        )
        used: set[int] = set()

        def _completed_ts(r: dict[str, Any]) -> int | None:
            """Round completion time as a UTC epoch, or None if unparseable.
            Built from `completed_iso` (HH:MM:SS) + the day's midnight."""
            iso = r.get("completed_iso")
            if not iso:
                return None
            try:
                h, m, s = (int(x) for x in str(iso).split(":"))
                return midnight_ts + h * 3600 + m * 60 + s
            except Exception:
                return None

        # Greedy in completion order so earlier rounds claim first; rounds with
        # no parseable completion time sink to the end and are skipped.
        order = sorted(
            range(len(rounds)),
            key=lambda i: (_completed_ts(rounds[i]) is None, _completed_ts(rounds[i]) or 0),
        )
        matches: dict[int, tuple[str, float]] = {}

        def _do_pass(back_pad: int, fwd_pad: int) -> None:
            """Run one greedy pass: each unmatched participation claims the
            unused transfer nearest its completion time, within `back_pad`
            before completion and `fwd_pad` after (asymmetric -- rewards
            post-date the round, so backward is only clock-skew slack).
            Prefers transfers at/after completion. Updates `matches`/`used`."""
            for orig_i in order:
                if orig_i in matches:
                    continue  # already matched in a previous pass
                r = rounds[orig_i]
                if r.get("tx_hash"):
                    continue  # already has agent-attached tx
                # Skip observer rounds. Default to True for backward compat
                # with pre-v8.6 snapshots that don't emit `participated`.
                if r.get("participated", True) is False:
                    continue
                completed_ts = _completed_ts(r)
                if completed_ts is None:
                    continue
                lo = completed_ts - back_pad
                hi = completed_ts + fwd_pad
                best_ai = None
                best_key: tuple[int, int] | None = None
                for ai, (ts, _tx, _amt) in enumerate(avail):
                    if ai in used:
                        continue
                    if ts < lo or ts > hi:
                        continue
                    # Forward bias: at/after-completion transfers (group 0) rank
                    # ahead of pre-completion ones (group 1), then by closeness
                    # to completion. The only reason to match a pre-completion
                    # transfer is clock skew, so it's a last resort.
                    key = (0 if ts >= completed_ts else 1, abs(ts - completed_ts))
                    if best_key is None or key < best_key:
                        best_key = key
                        best_ai = ai
                if best_ai is not None:
                    used.add(best_ai)
                    matches[orig_i] = (avail[best_ai][1], avail[best_ai][2])

        # Pass 1: strict symmetric window (back side is just clock-skew slack).
        _do_pass(pad_seconds, pad_seconds)
        # Pass 2: relaxed -- extend FORWARD only for deferred resolution.
        # Backward stays at pad_seconds: a transfer that landed >5 min before a
        # round completed can't be its reward, and widening backward to 30 min
        # is exactly how a later round used to steal an earlier round's tx.
        # Forward reach is env-tunable (MATCH_RELAXED_MINUTES, default 30 min).
        _do_pass(pad_seconds, _RELAXED_PAD_SECONDS)

        # Pass 3 (sequential inter-round gap-fill): a round's reward often only
        # lands on-chain by the time the NEXT round begins -- past the relaxed
        # window above, or after the last scan for the most recent round. For
        # each still-unmatched participation, in completion order, claim the
        # earliest unused transfer in the gap [this completion, next completion);
        # open-ended for the most recent round. `avail` is ts-sorted, so the
        # first in-gap hit is the earliest. Additive only: never touches rounds
        # already matched / agent-attached, never re-claims a used transfer.
        def _do_gap_pass() -> None:
            seq = [i for i in order if _completed_ts(rounds[i]) is not None]
            for pos, orig_i in enumerate(seq):
                r = rounds[orig_i]
                if orig_i in matches or r.get("tx_hash"):
                    continue
                if r.get("participated", True) is False:
                    continue
                ci = _completed_ts(r)
                c_next = _completed_ts(rounds[seq[pos + 1]]) if pos + 1 < len(seq) else None
                for ai, (ts, _tx, _amt) in enumerate(avail):
                    if ai in used or ts < ci:
                        continue
                    if c_next is not None and ts >= c_next:
                        break  # ts-sorted: no later transfer can be in-gap either
                    used.add(ai)
                    matches[orig_i] = (avail[ai][1], avail[ai][2])
                    break

        _do_gap_pass()

        # Rebuild in original order with matched tx_hash + reward_amount
        # injected. reward_amount lets persisters (the rounds table) capture
        # the per-round payout without re-running the matcher themselves.
        out: list[dict[str, Any]] = []
        for i, r in enumerate(rounds):
            if i in matches:
                tx, amt = matches[i]
                r2 = dict(r)
                r2["tx_hash"] = tx
                r2["reward_amount"] = amt
                out.append(r2)
            else:
                out.append(r)
        return out

    def summary(self) -> dict[str, Any]:
        earned = sum(t.amount for t in self.today_transfers)
        count = len(self.today_transfers)
        last = self.today_transfers[-1] if self.today_transfers else None
        # Bucket transfers by UTC hour. Keys match the agent's
        # rounds_history format ("YYYY-MM-DDTHH") so the dashboard's
        # bucket() helper can reuse the same lookup pattern for tooltips.
        # Includes today + yesterday (in-memory) + historical (SQLite),
        # so 24h / 7d / 4w chart bars all get per-hour FOR data when
        # the corresponding day was scanned at some point.
        by_hour: dict[str, float] = dict(self.historical_by_hour)  # start with persisted history
        # Today + yesterday in-memory state takes precedence (more recent)
        for t in (*self.today_transfers, *self.yesterday_transfers):
            dt = datetime.fromtimestamp(t.ts, tz=timezone.utc)
            key = dt.strftime("%Y-%m-%dT%H")
            # Recompute the hour bucket from the live list — for today this
            # is more accurate than historical (historical is a snapshot,
            # today is the source of truth).
            if key.startswith(self.today_utc_date or "_"):
                # Will be overwritten below in the second pass for today's keys
                by_hour[key] = 0.0
        for t in (*self.today_transfers, *self.yesterday_transfers):
            dt = datetime.fromtimestamp(t.ts, tz=timezone.utc)
            key = dt.strftime("%Y-%m-%dT%H")
            by_hour[key] = by_hour.get(key, 0.0) + t.amount
        by_hour_rounded = {k: round(v, 6) for k, v in by_hour.items()}
        return {
            "earned_today": round(earned, 6) if earned else 0.0,
            "transfers_today": count,
            "transfers_by_hour": by_hour_rounded,
            "last_transfer_amount": round(last.amount, 6) if last else None,
            "last_transfer_iso": last.iso if last else None,
            "last_transfer_tx": last.tx_hash if last else None,
            "refreshed_at": self.last_refresh_ts or None,
            "error": self.last_error,
        }


_trackers: dict[str, RewardsTracker] = {}


def get_tracker(wallet: str) -> RewardsTracker:
    """Return (creating if needed) the tracker for the given operator wallet."""
    wlc = wallet.lower()
    if wlc not in _trackers:
        _trackers[wlc] = RewardsTracker(wallet=wlc)
    return _trackers[wlc]


def known_tracker_wallets() -> list[str]:
    return list(_trackers.keys())


# --- Earnings projection --------------------------------------------------
# Below the threshold, today's pace is too noisy to extrapolate (one early
# reward in hour 0 would project to 24x weekly). Card falls back to the
# 7-day average alone until we're this far into UTC day.
_PROJECTION_MIN_HOURS_ELAPSED = 1.0


def projections(wallet: str) -> dict[str, Any]:
    """Card-ready earnings projection for the operator wallet.

    Combines two signals:
      - "Today's pace": earned_today extrapolated from elapsed UTC hours.
        Suppressed before _PROJECTION_MIN_HOURS_ELAPSED to dodge noise.
      - "7-day average": mean of the last 7 *complete* UTC days from
        daily_totals (today excluded — it's a partial day).

    Both are returned; the dashboard decides which to surface and how.
    Numbers are returned raw (not rounded) so the client picks the right
    precision per slot."""
    tracker = get_tracker(wallet)
    s = tracker.summary()
    earned_today = float(s.get("earned_today") or 0.0)

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hours_elapsed = max(0.0, (now - midnight).total_seconds() / 3600.0)

    today_pace_per_hour: float | None = None
    today_projected_daily: float | None = None
    today_projected_weekly: float | None = None
    today_projected_monthly: float | None = None
    if hours_elapsed >= _PROJECTION_MIN_HOURS_ELAPSED:
        today_pace_per_hour = earned_today / hours_elapsed
        today_projected_daily = today_pace_per_hour * 24.0
        today_projected_weekly = today_projected_daily * 7.0
        today_projected_monthly = today_projected_daily * 30.0

    # 7-day average from persisted daily_totals. We deliberately skip today
    # so the average reflects complete days only. Rows are already ordered
    # by utc_date ascending.
    days_used = 0
    sum_7d = 0.0
    try:
        rows = load_daily_totals(wallet)
    except Exception:
        rows = []
    for row in reversed(rows):
        if row.get("utc_date") == today_str:
            continue
        amount = row.get("total_amount")
        if amount is None:
            continue
        try:
            sum_7d += float(amount)
        except (TypeError, ValueError):
            continue
        days_used += 1
        if days_used >= 7:
            break

    avg_7d_daily: float | None = None
    avg_7d_weekly: float | None = None
    avg_7d_monthly: float | None = None
    if days_used > 0:
        avg_7d_daily = sum_7d / days_used
        avg_7d_weekly = avg_7d_daily * 7.0
        avg_7d_monthly = avg_7d_daily * 30.0

    return {
        "earned_today": earned_today,
        "hours_elapsed": round(hours_elapsed, 2),
        "today_pace_per_hour": today_pace_per_hour,
        "today_projected_daily": today_projected_daily,
        "today_projected_weekly": today_projected_weekly,
        "today_projected_monthly": today_projected_monthly,
        "avg_7d_daily": avg_7d_daily,
        "avg_7d_weekly": avg_7d_weekly,
        "avg_7d_monthly": avg_7d_monthly,
        "days_used_for_avg": days_used,
    }
