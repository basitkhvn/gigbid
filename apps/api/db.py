"""App database (users, profiles, runs, run events, saved searches). SQLite file; every query is tenant-scoped (user_id)."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from agent.config import ROOT
from apps.api.migrations import migrate

_conn: sqlite3.Connection | None = None


def db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        d = Path(os.environ.get("GIGBID_STATE_DIR", ROOT / "data/processed")); d.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(d / "app.sqlite", check_same_thread=False, isolation_level=None)
        _conn.row_factory = sqlite3.Row
        migrate(_conn)  # versioned schema, see apps/api/migrations.py
    return _conn


def row(r) -> dict | None:
    return dict(r) if r else None


def rows(q: str, *a) -> list[dict]:
    return [dict(r) for r in db().execute(q, a).fetchall()]


def one(q: str, *a) -> dict | None:
    return row(db().execute(q, a).fetchone())


def now() -> float:
    return time.time()


DEFAULT_SETTINGS = {"rate": 45, "floor": 30, "autonomy": "ask_always", "weekly_connects_budget": 120,
                    "connects_spent_this_week": 0, "marketplace": "gigsim", "filters": {"min_budget": 0}}


def get_settings(uid: str) -> dict:
    r = one("SELECT data FROM settings WHERE user_id=?", uid)
    return {**DEFAULT_SETTINGS, **(json.loads(r["data"]) if r else {})}


def save_settings(uid: str, data: dict) -> dict:
    cur = {**get_settings(uid), **data}
    db().execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (uid, json.dumps(cur)))
    return cur
