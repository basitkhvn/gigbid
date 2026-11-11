import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from agent.tracing import read_trace, summarize
from apps.api import runs
from apps.api.auth.users import current_user
from apps.api.db import one, rows

router = APIRouter(prefix="/runs", tags=["runs"])


def _own(run_id: str, user: dict) -> dict:
    r = one("SELECT * FROM runs WHERE id=? AND user_id=?", run_id, user["id"])
    if not r:
        raise HTTPException(404, "run not found")
    return r


@router.get("")
def list_runs(user: dict = Depends(current_user)):
    return rows("SELECT id,kind,job_id,status,category,title,created,updated,trace_id FROM runs WHERE user_id=? ORDER BY updated DESC LIMIT 100", user["id"])


@router.get("/{run_id}")
def get_run(run_id: str, user: dict = Depends(current_user)):
    r = _own(run_id, user)
    ev = rows("SELECT id,ts,node,data FROM run_events WHERE run_id=? ORDER BY id", run_id)
    return {"run": r, "events": [{**e, "data": json.loads(e["data"])} for e in ev], "trace": summarize(r["trace_id"]) if r["trace_id"] else None}


@router.get("/{run_id}/stream")
async def stream(run_id: str, request: Request, user: dict = Depends(current_user)):
    """SSE: live node-by-node progress. Replays from the event log, so a page refresh never loses progress."""
    _own(run_id, user)

    async def gen():
        last = 0
        while True:
            if await request.is_disconnected():
                break
            evs = rows("SELECT id,ts,node,data FROM run_events WHERE run_id=? AND id>? ORDER BY id", run_id, last)
            for e in evs:
                last = e["id"]
                yield {"event": "node", "data": json.dumps({"node": e["node"], "ts": e["ts"], **json.loads(e["data"])})}
                if e["node"] in ("__end__", "__error__"):
                    return
            st = one("SELECT status FROM runs WHERE id=?", run_id)
            if st and st["status"] not in ("running",) and not evs:
                yield {"event": "node", "data": json.dumps({"node": "__end__", "status": st["status"]})}
                return
            await asyncio.sleep(0.4)
    return EventSourceResponse(gen())


@router.get("/{run_id}/trace")
def trace(run_id: str, user: dict = Depends(current_user)):
    r = _own(run_id, user)
    return {"summary": summarize(r["trace_id"]), "spans": read_trace(r["trace_id"])}


@router.get("/{run_id}/history")
async def history(run_id: str, user: dict = Depends(current_user)):
    """Checkpoint history: replay a job from any node (C6)."""
    r = _own(run_id, user)
    out = []
    async for s in runs.GRAPHS[r["kind"]].aget_state_history(runs.cfg_of(run_id)):
        out.append({"checkpoint_id": s.config["configurable"]["checkpoint_id"], "next": list(s.next), "step": s.metadata.get("step"),
                    "status": s.values.get("status")})
    return out


@router.post("/{run_id}/replay/{checkpoint_id}")
async def replay(run_id: str, checkpoint_id: str, user: dict = Depends(current_user)):
    r = _own(run_id, user)
    cfg = {"configurable": {**runs.cfg_of(run_id)["configurable"], "checkpoint_id": checkpoint_id}}
    runs._set(run_id, status="running")
    runs.TASKS[run_id] = asyncio.create_task(runs._drive(run_id, r["kind"], None, cfg))
    return {"ok": True}
