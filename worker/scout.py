"""Scheduled scouting (E1): polite, idempotent. Each saved search has its own interval (default 4h, min 60 min; live mode
defaults higher, see docs/RUNBOOK.md). Re-running never double-analyses: Scout de-dups by text fingerprint and triage results
are cached per (user, job)."""
from __future__ import annotations

import time

from agent.nodes.scout import already_seen, mark_if_new
from agent.mcp_client import ToolUnavailable, get_hub
from apps.api.db import db, now, rows
from apps.api.triage import triage_job

CATEGORY = {"ml": "AI & Machine Learning", "web": "Web Development", "data": "Data Analysis"}


async def scout_user_search(user: dict, s: dict) -> int:
    res = await get_hub().call("scout", "search_jobs", {"user_id": user["id"], "q": s["q"], "category": s["category"] or CATEGORY[user["persona"]],
                                                       "skill": s["skill"], "limit": 25})
    n = 0
    for job in res["jobs"]:
        if not already_seen(user["id"], job) and mark_if_new(user["id"], job):
            await triage_job(user, job)
            n += 1
    return n


async def scout_due(now_ts: float | None = None) -> dict:
    """One scheduler tick: run every saved search whose interval has elapsed. Safe to call concurrently/repeatedly."""
    now_ts = now_ts or time.time()
    done = {}
    for s in rows("SELECT * FROM saved_searches"):
        if now_ts - s["last_run"] < s["interval_min"] * 60:
            continue
        user = db().execute("SELECT id,email,persona FROM users WHERE id=?", (s["user_id"],)).fetchone()
        if not user:
            continue
        db().execute("UPDATE saved_searches SET last_run=? WHERE id=?", (now_ts, s["id"]))  # claim first: a crash never double-runs
        try:
            done[s["id"]] = await scout_user_search(dict(user), s)
        except ToolUnavailable as e:
            db().execute("UPDATE saved_searches SET last_run=0 WHERE id=?", (s["id"],))  # retry next tick
            done[s["id"]] = f"queued: {e}"
    return done
