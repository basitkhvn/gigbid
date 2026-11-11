import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agent.llm import complete, prompt
from agent.mcp_client import ToolUnavailable, get_hub
from apps.api import runs
from apps.api.auth.users import current_user
from apps.api.db import one, rows
from apps.api.routers.approvals import pending_payload

router = APIRouter(tags=["proposals"])
COLUMNS = ["drafted", "submitted", "viewed", "replied", "interview", "hired", "lost"]
MAP = {"ignored": "lost", "viewed": "viewed", "replied": "replied", "interview": "interview", "hired": "hired"}


@router.get("/proposals/{run_id}")
async def studio(run_id: str, user: dict = Depends(current_user)):
    """Everything the Proposal Studio needs: draft, claims -> evidence, critic/compliance comments, price, dry_run preview."""
    run = one("SELECT * FROM runs WHERE id=? AND user_id=?", run_id, user["id"])
    if not run:
        raise HTTPException(404)
    st = await runs.GRAPHS[run["kind"]].aget_state(runs.cfg_of(run_id))
    v = st.values
    return {"run": run, "draft": v.get("draft"), "evidence": v.get("evidence", []), "critiques": v.get("critiques", []),
            "compliance": v.get("compliance"), "price_quote": v.get("price_quote"), "risk_report": v.get("risk_report"),
            "fit_report": v.get("fit_report"), "claim_stats": v.get("claim_stats"), "preview": v.get("preview"),
            "job_spec": v.get("job_spec"), "decision": v.get("decision"), "approval": v.get("approval"),
            "pending": bool(st.next), "submission": v.get("submission")}


class Regen(BaseModel):
    paragraph: str
    instruction: str = "Rewrite this paragraph more specifically; keep every [E#] citation valid; do not add new claims."


@router.post("/proposals/{run_id}/regenerate")
async def regenerate(run_id: str, body: Regen, user: dict = Depends(current_user)):
    run = one("SELECT * FROM runs WHERE id=? AND user_id=?", run_id, user["id"])
    if not run:
        raise HTTPException(404)
    res = complete("writer", prompt("writer", style_rules=""), f"{body.instruction}\n\nPARAGRAPH:\n{body.paragraph}")
    return {"paragraph": res.text.strip() if res else body.paragraph, "changed": bool(res)}


@router.get("/pipeline")
async def pipeline(user: dict = Depends(current_user)):
    board = {c: [] for c in COLUMNS}
    for r in rows("SELECT * FROM runs WHERE user_id=? AND kind='bid' AND status IN ('awaiting_approval','running')", user["id"]):
        board["drafted"].append({"id": r["id"], "title": r["title"], "run_id": r["id"], "status": r["status"]})
    try:
        props = (await get_hub().call("ui", "list_proposals", {"user_id": user["id"]}))["proposals"]
    except ToolUnavailable as e:
        return {"columns": board, "unavailable": str(e)}
    for p in props:
        col = MAP.get(p["status"], "submitted")
        job = one("SELECT title FROM runs WHERE user_id=? AND job_id=? AND kind='bid'", user["id"], p["job_id"])
        board[col].append({"id": p["proposal_id"], "title": (job or {}).get("title", p["job_id"]), "job_id": p["job_id"],
                           "bid": p["bid"], "connects": p["connects_spent"]})
    return {"columns": board}
