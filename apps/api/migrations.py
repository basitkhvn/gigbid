"""Versioned, forward-only schema migrations for the app DB.

Add a new entry at the END of MIGRATIONS; never edit an applied one. Applied versions are
recorded in `schema_migrations`, each migration runs in a transaction, and `migrate()` is
idempotent. Migration 1 is the baseline and uses IF NOT EXISTS so databases created before
this runner existed are adopted without data loss.
"""
from __future__ import annotations

import sqlite3
import time

MIGRATIONS: list[tuple[int, str, str]] = [
    (1, "baseline", """
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT UNIQUE, pw TEXT, persona TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS settings(user_id TEXT PRIMARY KEY, data TEXT);
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, user_id TEXT, kind TEXT, job_id TEXT, proposal_id TEXT,
            trace_id TEXT, status TEXT, category TEXT, title TEXT, created REAL, updated REAL, summary TEXT);
        CREATE TABLE IF NOT EXISTS run_events(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts REAL, node TEXT, data TEXT);
        CREATE TABLE IF NOT EXISTS saved_searches(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, q TEXT, category TEXT,
            skill TEXT, interval_min INTEGER DEFAULT 240, last_run REAL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS tokens(user_id TEXT, provider TEXT, blob BLOB, PRIMARY KEY(user_id, provider));
        CREATE INDEX IF NOT EXISTS ev_run ON run_events(run_id, id);
    """),
    (2, "triage table", """
        CREATE TABLE IF NOT EXISTS triage(user_id TEXT, job_id TEXT, data TEXT, ts REAL, PRIMARY KEY(user_id, job_id));
    """),
    (3, "runs index by user", """
        CREATE INDEX IF NOT EXISTS runs_user ON runs(user_id, created);
    """),
]


def current_version(conn: sqlite3.Connection) -> int:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, name TEXT, applied REAL)")
    r = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    return r[0] or 0


def migrate(conn: sqlite3.Connection) -> int:
    """Apply pending migrations in order; return the resulting schema version."""
    cur = current_version(conn)
    for version, name, sql in MIGRATIONS:
        if version <= cur:
            continue
        try:
            conn.execute("BEGIN")
            for stmt in (s.strip() for s in sql.split(";")):
                if stmt:
                    conn.execute(stmt)
            conn.execute("INSERT INTO schema_migrations VALUES (?,?,?)", (version, name, time.time()))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    return max(cur, MIGRATIONS[-1][0])
