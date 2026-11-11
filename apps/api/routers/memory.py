from fastapi import APIRouter, Depends

from agent.memory.store import delete_memory, list_memories
from apps.api.auth.users import current_user

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("")
def view(user: dict = Depends(current_user)):
    """What GigBid has learned (promoted knowledge only) plus not-yet-promoted candidates, so the user can see the rule at work."""
    return {"style": list_memories(user["id"], "style"), "outcome": list_memories(user["id"], "outcome"),
            "style_candidates": list_memories(user["id"], "style_candidates")}


@router.delete("/{kind}/{key:path}")
def forget(kind: str, key: str, user: dict = Depends(current_user)):
    if kind in ("style", "outcome", "style_candidates"):
        delete_memory(user["id"], kind, key)
    return {"ok": True}
