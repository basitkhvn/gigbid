"""Live Upwork adapter (A4): maps the official Upwork MCP server's tools onto the marketplace port.

Connects via langchain-mcp-adapters' MultiServerMCPClient over Streamable HTTP with the user's OAuth 2.1 bearer
token (stored encrypted per user by apps/api/auth/tokens.py). Constraints enforced HERE and not relaxable by agents:
  * write tools only create DRAFTS; the user confirms on Upwork;
  * reads are rate-limited to >= UPWORK_MIN_INTERVAL_S between calls per user (no scraping-like polling);
  * no browser automation, cookies or page fetching exist in this module.

STATUS: implemented against the documented tool surface but NOT exercised against a real account in this repo
(no Upwork credentials were available). Tool names live in TOOL_MAP so they can be corrected from `list_tools()`.
"""
from __future__ import annotations

import os
import time
from typing import Any

from mcp_servers.marketplace.adapters.base import MarketplaceUnavailable

UPWORK_MCP_URL = os.environ.get("UPWORK_MCP_URL", "https://mcp.upwork.com/mcp")
MIN_INTERVAL = float(os.environ.get("UPWORK_MIN_INTERVAL_S", "30"))
TOOL_MAP = {  # port operation -> upwork tool name (verify with list_tools at connect time)
    "search_jobs": "search_jobs", "get_job": "get_job", "get_client": "get_client_profile",
    "list_messages": "list_messages", "create_draft": "create_proposal_draft", "send_message": "create_message_draft",
}


class UpworkLiveAdapter:
    name = "upwork_live"

    def __init__(self, token_provider):
        self.token_provider = token_provider  # callable(user) -> decrypted access token
        self._last: dict[str, float] = {}

    async def _call(self, user: str, op: str, args: dict[str, Any]) -> Any:
        now = time.time()
        if now - self._last.get(user, 0) < MIN_INTERVAL and op.startswith(("search", "get", "list")):
            raise MarketplaceUnavailable(f"live read throttled: min interval {MIN_INTERVAL}s")
        self._last[user] = now
        from langchain_mcp_adapters.client import MultiServerMCPClient
        client = MultiServerMCPClient({"upwork": {"url": UPWORK_MCP_URL, "transport": "streamable_http",
                                                   "headers": {"Authorization": f"Bearer {self.token_provider(user)}"}}})
        try:
            tools = {t.name: t for t in await client.get_tools()}
            return await tools[TOOL_MAP[op]].ainvoke(args)
        except Exception as e:  # noqa: BLE001
            raise MarketplaceUnavailable(f"upwork mcp error: {e}") from e

    async def search_jobs(self, user, q, category, skill, limit, offset): return await self._call(user, "search_jobs", {"query": q, "limit": limit})
    async def get_job(self, user, job_id): return await self._call(user, "get_job", {"job_id": job_id})
    async def get_client(self, user, client_id): return await self._call(user, "get_client", {"client_id": client_id})
    async def get_connects(self, user): return {"balance": None, "note": "see Upwork account"}
    async def get_price_stats(self, user, category): return {"n": 0}
    async def get_policy(self, user): return {"version": "upwork-live"}
    async def list_messages(self, user, proposal_id): return await self._call(user, "list_messages", {"proposal_id": proposal_id})
    async def list_threads(self, user): return {}
    async def list_proposals(self, user): return []

    async def submit_proposal(self, user, payload):  # creates a DRAFT only; user confirms on Upwork
        r = await self._call(user, "create_draft", payload)
        return {"proposal_id": str(r), "status": "draft_on_upwork_awaiting_user_confirmation", "connects_spent": 0}

    async def send_message(self, user, payload):
        r = await self._call(user, "send_message", payload)
        return {"status": "draft_on_upwork_awaiting_user_confirmation", "result": str(r)}
