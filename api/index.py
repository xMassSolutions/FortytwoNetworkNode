"""Vercel Python entrypoint -- exposes the FastAPI ASGI app so Vercel can run it
as a serverless function. `vercel.json` rewrites the API paths (/v1, /login,
/healthz, /api/cron/*) here; the rest is served from the built SPA.

The server package lives in ../server, so put it on sys.path before importing.
Requires the same env as Render (AGENT_TOKEN, WALLET, DATABASE_URL, REDIS_URL,
DASHBOARD_USER/DASHBOARD_PASS_HASH, SESSION_SECRET, CRON_SECRET, RUN_BG_LOOPS=0)
to be set in the Vercel project.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from app import app  # noqa: E402  -- path is set above

# Vercel's Python runtime serves the module-level `app` ASGI callable.
