"""Schema snapshot test: fails CI when an MCP tool signature changes unintentionally.
Intentional change: UPDATE_SNAPSHOTS=1 pytest tests/contract && commit the new snapshot."""
import asyncio
import json
import os
from pathlib import Path

from mcp_servers.marketplace.server import create_server as market
from mcp_servers.portfolio.server import create_server as portfolio
from mcp_servers.workspace.server import create_server as workspace

SNAP = Path(__file__).parent / "snapshots" / "tools.json"


def current():
    out = {}
    for name, f in (("marketplace", market), ("portfolio", portfolio), ("workspace", workspace)):
        tools = asyncio.run(f().list_tools())
        out[name] = {t.name: {"inputSchema": t.inputSchema, "annotations": t.annotations.model_dump(exclude_none=True) if t.annotations else {}}
                     for t in tools}
    return json.loads(json.dumps(out, sort_keys=True))


def test_tool_signatures_unchanged():
    cur = current()
    if os.environ.get("UPDATE_SNAPSHOTS") or not SNAP.exists():
        SNAP.write_text(json.dumps(cur, indent=1, sort_keys=True))
    assert cur == json.loads(SNAP.read_text()), "MCP tool schema changed; review and UPDATE_SNAPSHOTS=1 if intended"


def test_write_tools_declare_annotations_and_idempotency():
    cur = current()["marketplace"]
    for name in ("create_proposal_draft", "submit_proposal", "send_message"):
        t = cur[name]
        assert t["annotations"]["readOnlyHint"] is False
        assert "idempotency_key" in json.dumps(t["inputSchema"])
    for name in ("search_jobs", "get_job", "get_client_history", "get_connects_balance", "list_messages"):
        assert cur[name]["annotations"]["readOnlyHint"] is True
    assert all(t["annotations"]["readOnlyHint"] for t in current()["portfolio"].values())
