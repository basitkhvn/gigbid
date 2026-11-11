from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from apps.api import runs
from apps.api.auth.users import current_user
from apps.api.db import db, one, rows, now
import json

router = APIRouter(prefix="/approvals", tags=["approvals"])


class Decision(BaseModel):
    action: Literal["approve", "edit", "reject"]
    text: str = Field(default="", max_length=6000, description="edited text (action=edit)")
    reason: str = Field(default="", max_length=500, description="required when rejecting")


async def pending_payload(run: dict) -> dict | None:
    st = await runs.GRAPHS[run["kind"]].aget_state(runs.cfg_of(run["id"]))
    for t in st.tasks:
        if t.interrupts:
            return t.interrupts[0].value
    return None


@router.get("")
async def list_pending(user: dict = Depends(current_user)):
    """Survives refresh/crash: pending approvals are read from the LangGraph checkpoint, not from memory."""
    out = []
    for r in rows("SELECT * FROM runs WHERE user_id=? AND status='awaiting_approval' ORDER BY updated DESC", user["id"]):
        p = await pending_payload(r)
        if p:
            out.append({"run_id": r["id"], "kind": r["kind"], "title": r["title"], "payload": p})
    return out


@router.post("/{run_id}")
async def decide(run_id: str, d: Decision, user: dict = Depends(current_user)):
    run = one("SELECT * FROM runs WHERE id=? AND user_id=?", run_id, user["id"])
    if not run:
        raise HTTPException(404, "run not found")
    if run["status"] != "awaiting_approval":
        raise HTTPException(409, f"run is {run['status']}, nothing to approve")
    if d.action == "reject" and not d.reason.strip():
        raise HTTPException(422, "a reason is required when rejecting")
    if d.action == "edit" and not d.text.strip():
        raise HTTPException(422, "edited text is required")
    runs.resume(run_id, run["kind"], d.model_dump())
    return {"ok": True, "run_id": run_id}
