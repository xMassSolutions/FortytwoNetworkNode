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
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS wallets (
            address    TEXT PRIMARY KEY,
            label      TEXT,
            added_at   INTEGER NOT NULL
        );
        """)
        conn.commit()
