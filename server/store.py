import json
from dataclasses import asdict, dataclass, field
from typing import Any

import db


@dataclass
class Snapshot:
    received_at: float
    ts: str = ""
    # Numeric node identifier. Default 1 preserves single-node behavior for
    # legacy agents that don't send the field.
    node_id: int = 1
    # Per-node operator wallet. When None, callers fall back to the server's
    # WALLET env var (back-compat for un-upgraded agents).
    node_wallet: str | None = None
    # Short git SHA of the agent's checked-out code — surfaces in dashboard
    # so operators can see which version each node is running.
    agent_version: str | None = None
    model: str | None = None
    model_short: str | None = None
    model_size_gb: float | None = None
    # v9.1 diagnostic — model-search breadcrumbs from the PS agent (None on
    # macOS/Linux). Surfaced raw in /v1/dashboard-data for debugging only.
    model_debug: dict[str, Any] | None = None
    capsule_max_tps: int | None = None
    capsule_version: str | None = None
    protocol_version: str | None = None
    capsule_uptime_seconds: int | None = None
    rounds_participated_today: int = 0
    rounds_observed_today: int = 0
    errors_today: int = 0
    first_round_today_iso: str | None = None
    last_round_today_iso: str | None = None
    last_round_duration_s: int | None = None
    last_reward_amount: float | None = None
    last_reward_iso: str | None = None
    rewards_today_total: float | None = None
    wins_today: int = 0
    # Count of `Participant's FOR balance before/after reward` pairs today
    # where after > before — i.e., rewards that landed inside the Capsule's
    # ~7-second snapshot window. wins_today now mirrors participations; this
    # field is the diagnostic for how many rewards were captured in-window.
    rewards_logged_today: int = 0
    tps_current: float | None = None
    symbols_current: float | None = None
    max_symbols: float | None = None
    gpu_name: str | None = None
    gpu_vram_used_mb: int | None = None
    gpu_vram_total_mb: int | None = None
    gpu_power_w: float | None = None
    capsule_pid: int | None = None
    protocol_pid: int | None = None
    capsule_alive: bool = False
    protocol_alive: bool = False
    recent_rounds: list[dict[str, Any]] = field(default_factory=list)
    all_rounds_today: list[dict[str, Any]] = field(default_factory=list)
    rounds_history: dict[str, int] = field(default_factory=dict)
    recent_errors: list[dict[str, Any]] = field(default_factory=list)
    log_extended: list[str] = field(default_factory=list)
    log_capsule: list[str] = field(default_factory=list)


class Store:
    """Latest snapshot per node. In-memory for speed (the warm path), with a
    durable mirror in the DB (`node_snapshots`) so a cold start -- a server
    restart or a fresh serverless invocation -- reloads the agent's last push
    instead of showing "no data"."""

    def __init__(self) -> None:
        self._latest: dict[int, Snapshot] = {}

    def set(self, snap: Snapshot) -> None:
        self._latest[snap.node_id] = snap
        # Write-through to the durable mirror. Best-effort -- a DB hiccup must
        # never drop an agent push (the in-memory copy already succeeded).
        try:
            db.upsert_node_snapshot(
                snap.node_id, snap.node_wallet,
                json.dumps(asdict(snap), separators=(",", ":"), default=str),
                snap.received_at,
            )
        except Exception:
            pass

    def get(self, node_id: int) -> Snapshot | None:
        s = self._latest.get(node_id)
        if s is not None:
            return s
        # Cold path: rehydrate from the durable mirror and cache it.
        s = _load_snapshot(node_id)
        if s is not None:
            self._latest[node_id] = s
        return s

    def known_node_ids(self) -> list[int]:
        ids = set(self._latest.keys())
        try:
            ids.update(int(r["node_id"]) for r in db.load_all_node_snapshots())
        except Exception:
            pass
        return sorted(ids)

    def wallet_for(self, node_id: int) -> str | None:
        s = self.get(node_id)
        return s.node_wallet if s else None


_SNAP_FIELDS = set(Snapshot.__dataclass_fields__)


def _load_snapshot(node_id: int) -> Snapshot | None:
    try:
        row = db.load_node_snapshot(node_id)
        if not row:
            return None
        d = json.loads(row["payload"])
        # Tolerate schema drift -- only pass keys that are still Snapshot fields.
        return Snapshot(**{k: v for k, v in d.items() if k in _SNAP_FIELDS})
    except Exception:
        return None


store = Store()
