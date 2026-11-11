"""Workspace MCP server (A3): free calendar slots, tentative interview holds, email drafts.
Local mock backend (JSON files) so it runs anywhere; the Google Calendar/Gmail backend is a drop-in
(`BACKEND=google`) but is NOT implemented here: no OAuth credentials were provisioned. Agent-facing tools are identical.
Email 'drafts' are never sent: the tool only creates a draft."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from agent.config import ROOT

STATE = Path(os.environ.get("GIGBID_STATE_DIR", ROOT / "data/processed")) / "workspace.json"
RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
RW = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)


def _load() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"holds": {}, "drafts": {}}


def _save(d: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(d))


class HoldIn(BaseModel):
    user_id: str = Field(min_length=1)
    start: str = Field(description="ISO datetime")
    minutes: int = Field(default=30, ge=15, le=120)
    title: str = Field(min_length=1, max_length=120)
    idempotency_key: str = Field(min_length=8)


class EmailDraftIn(BaseModel):
    user_id: str = Field(min_length=1)
    to: str = Field(max_length=200)
    subject: str = Field(max_length=200)
    body: str = Field(max_length=5000)
    idempotency_key: str = Field(min_length=8)


def create_server() -> FastMCP:
    mcp = FastMCP("gigbid-workspace")

    @mcp.tool(annotations=RO)
    def free_slots(user_id: str, days: int = 5, minutes: int = 30) -> dict:
        """Free 30-minute interview slots in working hours (10:00-16:00) over the next N days, excluding existing holds."""
        d = _load()
        busy = {h["start"] for h in d["holds"].values() if h["user"] == user_id}
        out, day = [], datetime(2026, 11, 12, 10)
        for i in range(max(1, min(days, 14))):
            for hr in (10, 11, 14, 15):
                s = (day + timedelta(days=i)).replace(hour=hr).isoformat()
                if s not in busy and (day + timedelta(days=i)).weekday() < 5:
                    out.append(s)
        return {"slots": out[:8], "minutes": minutes}

    @mcp.tool(annotations=RW)
    def create_interview_hold(inp: HoldIn) -> dict:
        """Create a TENTATIVE calendar hold. Idempotent by key."""
        d = _load()
        if inp.idempotency_key in d["holds"]:
            return d["holds"][inp.idempotency_key]
        rec = {"id": uuid.uuid4().hex[:8], "user": inp.user_id, "start": inp.start, "minutes": inp.minutes,
               "title": inp.title, "status": "tentative"}
        d["holds"][inp.idempotency_key] = rec
        _save(d)
        return rec

    @mcp.tool(annotations=RW)
    def create_email_draft(inp: EmailDraftIn) -> dict:
        """Create an email DRAFT (never sends). Idempotent by key."""
        d = _load()
        if inp.idempotency_key in d["drafts"]:
            return d["drafts"][inp.idempotency_key]
        rec = {"id": uuid.uuid4().hex[:8], "user": inp.user_id, "to": inp.to, "subject": inp.subject, "body": inp.body, "status": "draft"}
        d["drafts"][inp.idempotency_key] = rec
        _save(d)
        return rec

    return mcp


if __name__ == "__main__":
    import sys
    srv = create_server()
    if "--http" in sys.argv:  # Streamable HTTP for docker compose / remote hosts
        srv.settings.host, srv.settings.port = "0.0.0.0", int(os.environ.get("PORT", 8084))
        srv.run(transport="streamable-http")
    else:
        srv.run()
