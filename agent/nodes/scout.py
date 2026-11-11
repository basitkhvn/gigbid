"""Scout: pull a job through the marketplace MCP server (read) and de-duplicate by normalised-text hash."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3

from agent.config import ROOT
from agent.mcp_client import get_hub
from agent.nodes.common import node

_DB = None


def _seen():
    global _DB
    if _DB is None:
        p = ROOT / "data/processed"; p.mkdir(parents=True, exist_ok=True)
        _DB = sqlite3.connect(p / "scout_seen.sqlite", check_same_thread=False)
        _DB.execute("CREATE TABLE IF NOT EXISTS seen(user TEXT, h TEXT, job_id TEXT, PRIMARY KEY(user,h))")
    return _DB


def fingerprint(job: dict) -> str:
    t = re.sub(r"\W+", " ", (job["title"] + " " + job["description"]).lower()).strip()
    return hashlib.sha1(t.encode()).hexdigest()


def mark_if_new(user: str, job: dict) -> bool:
    db = _seen()
    h = fingerprint(job)
    row = db.execute("SELECT job_id FROM seen WHERE user=? AND h=?", (user, h)).fetchone()
    if row and row[0] != job["job_id"]:
        return False
    db.execute("INSERT OR IGNORE INTO seen VALUES (?,?,?)", (user, h, job["job_id"]))
    db.commit()
    return True


@node("scout")
async def scout(state):
    job = state.get("job") or await get_hub().call("scout", "get_job", {"user_id": state["user_id"], "job_id": state["job_id"]})
    if isinstance(job, str):
        job = json.loads(job)
    new = mark_if_new(state["user_id"], job)
    out = {"job": job, "duplicate": not new}
    if not new:
        out["status"] = "skipped_duplicate"
    return out
