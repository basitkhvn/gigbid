
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from agent.mcp_client import get_hub
from apps.api.auth.users import current_user
from apps.api.db import db, get_settings, rows, save_settings
from rag.corpus import invalidate
from rag.ingest.loaders import add_user_item

router = APIRouter(tags=["settings"])


class SettingsIn(BaseModel):
    rate: float | None = Field(default=None, gt=0, le=1000)
    floor: float | None = Field(default=None, gt=0, le=1000)
    autonomy: str | None = Field(default=None, pattern="^(ask_always|auto_skip)$")
    weekly_connects_budget: int | None = Field(default=None, ge=0, le=2000)
    marketplace: str | None = Field(default=None, pattern="^(gigsim|upwork_live)$")


@router.get("/settings")
def get(user: dict = Depends(current_user)):
    return get_settings(user["id"])


@router.put("/settings")
def put(s: SettingsIn, user: dict = Depends(current_user)):
    return save_settings(user["id"], s.model_dump(exclude_none=True))


class SearchIn(BaseModel):
    q: str = ""
    category: str = ""
    skill: str = ""
    interval_min: int = Field(default=240, ge=60, le=1440)


@router.get("/saved-searches")
def list_searches(user: dict = Depends(current_user)):
    return rows("SELECT * FROM saved_searches WHERE user_id=?", user["id"])


@router.post("/saved-searches")
def add_search(s: SearchIn, user: dict = Depends(current_user)):
    db().execute("INSERT INTO saved_searches(user_id,q,category,skill,interval_min) VALUES (?,?,?,?,?)",
                 (user["id"], s.q, s.category, s.skill, s.interval_min))
    return {"ok": True}


@router.delete("/saved-searches/{sid}")
def del_search(sid: int, user: dict = Depends(current_user)):
    db().execute("DELETE FROM saved_searches WHERE id=? AND user_id=?", (sid, user["id"]))
    return {"ok": True}


class ItemIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    text: str = Field(min_length=20, max_length=20000)
    type: str = Field(default="case_study", pattern="^(case_study|readme|review|cv)$")
    skills: list[str] = []
    industry: str | None = None


@router.post("/portfolio/items")
def add_item(it: ItemIn, user: dict = Depends(current_user)):
    """Upload portfolio material; incremental re-index (only the new item is embedded; others come from the cache)."""
    import uuid
    iid = f"{user['persona']}-user-{uuid.uuid4().hex[:6]}"
    add_user_item(user["persona"], {"id": iid, "type": it.type, "title": it.title, "text": it.text, "skills": it.skills,
                                    "project": iid, "industry": it.industry, "date": None})
    invalidate(user["persona"])
    return {"id": iid}


@router.get("/portfolio/skills")
async def skills(user: dict = Depends(current_user)):
    return await get_hub().call("ui", "list_skills", {"persona": user["persona"]})
