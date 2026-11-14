import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query

from agent.mcp_client import ToolUnavailable, get_hub
from apps.api import runs
from apps.api.auth.users import current_user
from apps.api.db import one
from apps.api.triage import triage_job

router = APIRouter(prefix="/jobs", tags=["jobs"])
CATEGORY = {"ml": "AI & Machine Learning", "web": "Web Development", "data": "Data Analysis"}


@router.get("")
async def inbox(skill: str = "", q: str = "", min_fit: float = 0.0, action: str = "", limit: int = Query(12, le=40), offset: int = 0,
                user: dict = Depends(current_user)):
    """New jobs ranked by fit, with risk badges, recommended action, price and Connects cost."""
    try:
        res = await get_hub().call("ui", "search_jobs", {"user_id": user["id"], "q": q, "category": CATEGORY[user["persona"]],
                                                       "skill": skill, "limit": limit, "offset": offset})
    except ToolUnavailable as e:
        raise HTTPException(503, f"marketplace unavailable: {e}")
    items = await asyncio.gather(*[triage_job(user, j) for j in res["jobs"]])
    out = []
    for j, t in zip(res["jobs"], items):
        run = one("SELECT id,status FROM runs WHERE user_id=? AND job_id=? ORDER BY created DESC", user["id"], j["job_id"])
        out.append({"job_id": j["job_id"], "title": j["title"], "category": j["category"], "budget": j["budget"], "skills": j["required_skills"],
                    "connects_cost": j["connects_cost"], "posted_at": j.get("posted_at"), "action": t["action"], "fit": t["fit"],
                    "risk": t["risk"], "flags": t["flags"], "price": t["price"], "run": run})
    out = [o for o in out if o["fit"] >= min_fit and (not action or o["action"] == action)]
    out.sort(key=lambda o: (-(o["action"] == "bid"), -o["fit"], o["risk"]))
    return {"total": res["total"], "jobs": out}


@router.get("/{job_id}")
async def job_detail(job_id: str, user: dict = Depends(current_user)):
    try:
        job = await get_hub().call("ui", "get_job", {"user_id": user["id"], "job_id": job_id})
    except ToolUnavailable as e:
        raise HTTPException(503, f"marketplace unavailable: {e}")
    t = await triage_job(user, job)
    client = None
    try:
        client = await get_hub().call("ui", "get_client_history", {"user_id": user["id"], "client_id": job["client_id"]})
    except Exception:  # noqa: BLE001
        pass
    run = one("SELECT id,status,trace_id FROM runs WHERE user_id=? AND job_id=? ORDER BY created DESC", user["id"], job_id)
    return {"job": job, "client": client, "triage": t, "run": run}


@router.post("/{job_id}/draft")
async def draft(job_id: str, user: dict = Depends(current_user)):
    """Start the full bid graph for this job (analysis -> price -> proposal -> verify -> critic -> compliance -> approval)."""
    try:
        job = await get_hub().call("ui", "get_job", {"user_id": user["id"], "job_id": job_id})
    except ToolUnavailable as e:
        raise HTTPException(503, f"marketplace unavailable: {e}")
    return {"run_id": await runs.enqueue_bid(user, job)}


@router.post("/{job_id}/skip")
async def skip(job_id: str, user: dict = Depends(current_user)):
    from apps.api.db import db, now
    db().execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 (f"skip:{user['id']}:{job_id}", user["id"], "skip", job_id, "", "", "skipped", "", job_id, now(), now(), "{}"))
    return {"ok": True}
