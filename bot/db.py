"""SQLite layer for FortytwoBot.

NOTE: On Render's free tier the underlying filesystem is ephemeral.
Data in this DB resets on every redeploy (and on most cold starts).
For persistence across redeploys, mount a persistent disk OR move to
Postgres (e.g. free Neon DB) by reading DATABASE_URL instead.
"""

import os
import sqlite3
import threading

DB_PATH = os.environ.get("DB_PATH", "/tmp/fortytwobot.db")
_lock = threading.Lock()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_schema() -> None:
    with _lock, get_conn() as conn:
        # daily_totals is non-authoritative cache and ephemeral on Render
        # anyway, so dropping legacy single-wallet rows is fine — they would
        # otherwise lack the new `wallet` column and PK.
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS wallets (
            address    TEXT PRIMARY KEY,
            label      TEXT,
            added_at   INTEGER NOT NULL
        );
        DROP TABLE IF EXISTS daily_totals;
        CREATE TABLE daily_totals (
            utc_date        TEXT NOT NULL,       -- "YYYY-MM-DD"
            wallet          TEXT NOT NULL,       -- lowercased 0x… operator wallet
            by_hour_json    TEXT NOT NULL,       -- {"YYYY-MM-DDTHH": amount}
            total_amount    REAL NOT NULL,
            transfer_count  INTEGER NOT NULL,
            last_updated    REAL NOT NULL,       -- epoch seconds
            PRIMARY KEY (utc_date, wallet)
        );
        """)
        conn.commit()


def upsert_daily_total(
    utc_date: str,
    wallet: str,
    by_hour: dict[str, float],
    total_amount: float,
    transfer_count: int,
    ts: float,
) -> None:
    import json
    with _lock, get_conn() as conn:
        conn.execute(
            """
            INSERT INTO daily_totals (utc_date, wallet, by_hour_json, total_amount, transfer_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(utc_date, wallet) DO UPDATE SET
                by_hour_json   = excluded.by_hour_json,
                total_amount   = excluded.total_amount,
                transfer_count = excluded.transfer_count,
                last_updated   = excluded.last_updated
            """,
            (utc_date, wallet.lower(), json.dumps(by_hour, separators=(",", ":")),
             total_amount, transfer_count, ts),
        )
        conn.commit()


def load_daily_totals(wallet: str) -> list[dict]:
    """Return list of {utc_date, by_hour, total_amount, transfer_count,
    last_updated} for the given wallet across every persisted day.
    Caller deserializes by_hour on demand."""
    import json
    rows: list[dict] = []
    with _lock, get_conn() as conn:
        for r in conn.execute(
            "SELECT utc_date, by_hour_json, total_amount, transfer_count, last_updated "
            "FROM daily_totals WHERE wallet = ? ORDER BY utc_date",
            (wallet.lower(),),
        ):
            try:
                by_hour = json.loads(r["by_hour_json"]) or {}
            except Exception:
                by_hour = {}
            rows.append({
                "utc_date": r["utc_date"],
                "by_hour": by_hour,
                "total_amount": r["total_amount"],
                "transfer_count": r["transfer_count"],
                "last_updated": r["last_updated"],
            })
    return rows
