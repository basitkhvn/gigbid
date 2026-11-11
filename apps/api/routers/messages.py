from fastapi import APIRouter, Depends, HTTPException

from agent.mcp_client import ToolUnavailable, get_hub
from apps.api import runs
from apps.api.auth.users import current_user
from apps.api.db import one

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("")
async def threads(user: dict = Depends(current_user)):
    try:
        t = (await get_hub().call("ui", "list_messages", {"user_id": user["id"], "proposal_id": ""}))["threads"]
    except ToolUnavailable as e:
        raise HTTPException(503, f"marketplace unavailable: {e}")
    out = []
    for pid, msgs in t.items():
        run = one("SELECT id,status FROM runs WHERE user_id=? AND proposal_id=? ORDER BY created DESC", user["id"], pid)
        out.append({"proposal_id": pid, "messages": msgs, "run": run})
    return out


@router.post("/{proposal_id}/suggest")
async def suggest(proposal_id: str, user: dict = Depends(current_user)):
    """Start the conversation graph: classify intent, draft a reply / interview slots, pause for approval."""
    return {"run_id": runs.start_conversation(user, proposal_id)}
