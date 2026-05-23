import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

import wallets as wstore
from chain import get_for_balance, get_native_balance
from dashboard_html import DASHBOARD_HTML
from db import init_schema
from rewards import tracker as rewards_tracker
from store import Snapshot, store

log = logging.getLogger("bot")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

AGENT_TOKEN = os.environ["AGENT_TOKEN"]
WALLET = os.environ["WALLET"]
FOR_CONTRACT = os.environ.get("FOR_CONTRACT", "0xf6B888f442277F01294F94D555608A2E8Bc86430")
MONAD_RPC_URL = os.environ.get("MONAD_RPC_URL", "https://testnet-rpc.monad.xyz/")

# Balance cache — at 5s dashboard refresh × N viewers, hitting Monad RPC every
# request gets us rate-limited. Cache the operator wallet balance for 30s.
_BALANCE_TTL = 30.0
_balance_cache: dict = {"value": None, "error": None, "ts": 0.0}


async def _cached_balance() -> tuple[float | None, str | None]:
    if time.time() - _balance_cache["ts"] < _BALANCE_TTL:
        return _balance_cache["value"], _balance_cache["error"]
    try:
        v = await get_for_balance(MONAD_RPC_URL, FOR_CONTRACT, WALLET)
        _balance_cache.update({"value": v, "error": None, "ts": time.time()})
        return v, None
    except Exception as e:
        msg = str(e)
        _balance_cache.update({"value": None, "error": msg, "ts": time.time()})
        return None, msg


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_schema()
    log.info("SQLite schema initialised")
    yield


app = FastAPI(lifespan=lifespan)


class StatusPayload(BaseModel):
    ts: str
    model: str | None = None
    model_short: str | None = None
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
    tps_current: float | None = None
    symbols_current: float | None = None
    max_symbols: float | None = None
    gpu_name: str | None = None
    gpu_vram_used_mb: int | None = None
    gpu_vram_total_mb: int | None = None
    capsule_pid: int | None = None
    protocol_pid: int | None = None
    capsule_alive: bool = False
    protocol_alive: bool = False
    recent_rounds: list[dict] = Field(default_factory=list)
    all_rounds_today: list[dict] = Field(default_factory=list)
    rounds_history: dict[str, int] = Field(default_factory=dict)
    recent_errors: list[dict] = Field(default_factory=list)
    log_extended: list[str] = Field(default_factory=list)
    log_capsule: list[str] = Field(default_factory=list)


def _require_agent_token(authorization: str | None) -> None:
    if authorization != f"Bearer {AGENT_TOKEN}":
        raise HTTPException(status_code=401, detail="invalid token")


@app.post("/v1/status")
async def v1_status(payload: StatusPayload, authorization: str = Header(None)):
    _require_agent_token(authorization)
    snap = Snapshot(received_at=time.time(), **payload.model_dump())
    store.set(snap)
    return {"ok": True, "received_at": snap.received_at}


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)


class AddWalletPayload(BaseModel):
    address: str
    label: str | None = None


@app.post("/v1/wallets")
async def add_wallet(payload: AddWalletPayload):
    try:
        addr = wstore.add_watched(payload.address, payload.label)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "address": addr}


@app.get("/v1/wallets")
async def list_wallets():
    rows = wstore.list_watched()
    enriched: list[dict] = []
    for w in rows:
        addr = w["address"]
        for_bal = None
        mon_bal = None
        try:
            for_bal = await get_for_balance(MONAD_RPC_URL, FOR_CONTRACT, addr)
        except Exception:
            pass
        try:
            mon_bal = await get_native_balance(MONAD_RPC_URL, addr)
        except Exception:
            pass
        enriched.append({
            "address": addr,
            "label": w.get("label"),
            "added_at": w.get("added_at"),
            "for_balance": for_bal,
            "monad_balance": mon_bal,
            "is_operator": addr.lower() == WALLET.lower(),
        })
    return {"wallets": enriched}


@app.get("/v1/dashboard-data")
async def dashboard_data():
    s = store.latest
    balance, balance_error = await _cached_balance()
    # Refresh on-chain rewards summary (30s in-memory cache inside the tracker
    # — same TTL as the balance cache). Wrapped in try/except so a Monad RPC
    # blip never blanks the rest of the dashboard.
    try:
        await rewards_tracker.refresh(MONAD_RPC_URL, FOR_CONTRACT, WALLET)
    except Exception as e:  # pragma: no cover — defensive
        log.warning("rewards tracker refresh failed: %s", e)
    chain_rewards = rewards_tracker.summary()

    snapshot_dict = None
    if s:
        snapshot_dict = {
            "received_at": s.received_at,
            "ts": s.ts,
            "model_short": s.model_short,
            "capsule_max_tps": s.capsule_max_tps,
            "capsule_version": s.capsule_version,
            "protocol_version": s.protocol_version,
            "capsule_uptime_seconds": s.capsule_uptime_seconds,
            "rounds_participated_today": s.rounds_participated_today,
            "rounds_observed_today": s.rounds_observed_today,
            "errors_today": s.errors_today,
            "first_round_today_iso": s.first_round_today_iso,
            "last_round_today_iso": s.last_round_today_iso,
            "last_round_duration_s": s.last_round_duration_s,
            "last_reward_amount": s.last_reward_amount,
            "last_reward_iso": s.last_reward_iso,
            "rewards_today_total": s.rewards_today_total,
            "wins_today": s.wins_today,
            "tps_current": s.tps_current,
            "symbols_current": s.symbols_current,
            "max_symbols": s.max_symbols,
            "gpu_name": s.gpu_name,
            "gpu_vram_used_mb": s.gpu_vram_used_mb,
            "gpu_vram_total_mb": s.gpu_vram_total_mb,
            "capsule_pid": s.capsule_pid,
            "protocol_pid": s.protocol_pid,
            "capsule_alive": s.capsule_alive,
            "protocol_alive": s.protocol_alive,
            "recent_rounds": s.recent_rounds,
            "all_rounds_today": s.all_rounds_today,
            "rounds_history": s.rounds_history,
            "recent_errors": s.recent_errors,
            "log_extended": s.log_extended,
            "log_capsule": s.log_capsule,
        }
    return JSONResponse({
        "snapshot": snapshot_dict,
        "balance": balance,
        "balance_error": balance_error,
        "chain_rewards": chain_rewards,
        "wallet": WALLET,
        "wallet_short": f"{WALLET[:6]}…{WALLET[-4:]}",
    })
