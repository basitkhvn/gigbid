"""ToolHub: the only way agents touch the outside world (A6).

* per-agent tool allowlists, filtered by name (least privilege);
* per-call timeout, bounded retries with exponential backoff;
* health tracking + degraded mode: when a server is down the hub raises ToolUnavailable so the graph can queue the
  work, and the API/UI shows a 'marketplace unavailable' banner (see /health/tools);
* transports: `inmemory` (servers run in-process; tests, single-container deploys) or `http`
  (MultiServerMCPClient over Streamable HTTP; docker compose).
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

from agent.config import load_config
from agent.tracing import current_trace, span

SERVER_OF = {  # tool -> server
    **{t: "marketplace" for t in ["search_jobs", "get_job", "get_client_history", "get_connects_balance", "get_price_stats",
                                  "get_platform_policy", "list_messages", "list_proposals", "create_proposal_draft",
                                  "submit_proposal", "send_message"]},
    **{t: "portfolio" for t in ["search_evidence", "get_case_study", "list_skills"]},
    **{t: "workspace" for t in ["free_slots", "create_interview_hold", "create_email_draft"]},
    "github_get_file_contents": "github",
}
ALLOWLIST: dict[str, set[str]] = {
    "scout": {"search_jobs", "get_job"},
    "analyst": set(),
    "risk_assessor": {"get_client_history", "get_job"},
    "fit_matcher": {"search_evidence", "get_case_study", "list_skills"},
    "pricing": {"get_price_stats", "get_connects_balance", "get_platform_policy"},
    "writer": {"search_evidence", "get_case_study"},
    "critic": {"search_evidence", "get_case_study"},
    "compliance": set(),
    "client_liaison": {"list_messages", "free_slots", "create_interview_hold", "create_email_draft", "search_evidence"},
    # runs ONLY after a human approved at an interrupt():
    "executor": {"create_proposal_draft", "submit_proposal", "send_message", "get_connects_balance"},
    "ingest": {"github_get_file_contents"},
    "ui": {"search_jobs", "get_job", "get_client_history", "get_connects_balance", "list_proposals", "list_messages",
           "get_platform_policy", "get_price_stats", "list_skills", "search_evidence", "get_case_study"},
}


class ToolUnavailable(Exception):
    pass


class ToolNotAllowed(Exception):
    pass


class ToolHub:
    def __init__(self, transport: str | None = None):
        cfg = load_config()["mcp"]
        self.transport = transport or os.environ.get("MCP_TRANSPORT", cfg["transport"])
        self.timeout, self.retries = cfg["timeout_s"], cfg["retries"]
        self.disabled: set[str] = set()
        self.health: dict[str, dict] = {}
        self._servers: dict[str, Any] = {}
        self._sessions: dict = {}
        self._holders: dict = {}

    # ---- in-memory servers
    def _server(self, name: str):
        if name not in self._servers:
            if name == "marketplace":
                from mcp_servers.marketplace.server import create_server
            elif name == "portfolio":
                from mcp_servers.portfolio.server import create_server
            elif name == "workspace":
                from mcp_servers.workspace.server import create_server
            else:
                raise ToolUnavailable(f"server {name} not configured")
            self._servers[name] = create_server()
        return self._servers[name]

    async def _invoke(self, server: str, tool: str, args: dict) -> Any:
        if self.transport == "http":
            from langchain_mcp_adapters.client import MultiServerMCPClient
            url = os.environ[f"MCP_{server.upper()}_URL"]
            headers = {"Authorization": f"Bearer {os.environ.get(f'MCP_{server.upper()}_TOKEN', '')}"}
            client = MultiServerMCPClient({server: {"url": url, "transport": "streamable_http", "headers": headers}})
            tools = {t.name: t for t in await client.get_tools()}
            return await tools[tool].ainvoke(args)
        s = await self._session(server)
        r = await s.call_tool(tool, args)
        if r.isError:
            raise RuntimeError(r.content[0].text if r.content else "tool error")
        if r.structuredContent is not None:
            sc = r.structuredContent
            return sc.get("result", sc) if isinstance(sc, dict) and list(sc) == ["result"] else sc
        txt = r.content[0].text if r.content else ""
        try:
            return json.loads(txt)
        except Exception:  # noqa: BLE001
            return txt

    async def _session(self, server: str):
        """One long-lived in-memory MCP client session per server per event loop (opening one per call burned CPU)."""
        loop = asyncio.get_running_loop()
        key = (server, id(loop))
        if key not in self._sessions:
            ready: asyncio.Future = loop.create_future()

            async def holder():
                from mcp.shared.memory import create_connected_server_and_client_session as conn
                try:
                    async with conn(self._server(server)._mcp_server) as sess:
                        ready.set_result(sess)
                        await asyncio.Event().wait()
                except Exception as e:  # noqa: BLE001
                    if not ready.done():
                        ready.set_exception(e)
            self._holders[key] = loop.create_task(holder())
            self._sessions[key] = await ready
        return self._sessions[key]

    async def call(self, agent: str, tool: str, args: dict | None = None, trace_id: str = "") -> Any:
        if tool not in ALLOWLIST.get(agent, set()):
            raise ToolNotAllowed(f"agent '{agent}' may not call '{tool}'")
        server = SERVER_OF[tool]
        args = dict(args or {})
        if server == "marketplace" and tool in ("create_proposal_draft", "submit_proposal", "send_message"):
            args.setdefault("trace_id", trace_id or current_trace.get())
        if server in self.disabled:
            self._mark(server, False, "disabled (simulated outage)")
            raise ToolUnavailable(f"{server} MCP server is unavailable")
        last: Exception | None = None
        with span(f"{server}.{tool}", kind="tool", agent=agent, args=args) as sp:
            for attempt in range(self.retries):
                try:
                    res = await asyncio.wait_for(self._invoke(server, tool, args), self.timeout)
                    self._mark(server, True)
                    sp["result_preview"] = str(res)[:300]
                    return res
                except (asyncio.TimeoutError, ConnectionError) as e:
                    last = e
                    await asyncio.sleep(min(0.3 * 2 ** attempt, 2))
                except Exception as e:  # noqa: BLE001
                    if "MARKETPLACE_UNAVAILABLE" in str(e):
                        last = e
                        await asyncio.sleep(min(0.3 * 2 ** attempt, 2))
                        continue
                    raise
            self._mark(server, False, repr(last))
            raise ToolUnavailable(f"{server} unavailable after {self.retries} attempts: {last}")

    def _mark(self, server: str, ok: bool, err: str = ""):
        self.health[server] = {"ok": ok, "ts": time.time(), "error": err}

    def status(self) -> dict:
        # NB: spread the stored health FIRST so the computed "ok" (which honours a simulated outage) is not overwritten by a stale value
        return {s: {**self.health.get(s, {}),
                    "ok": s not in self.disabled and self.health.get(s, {"ok": True})["ok"]} for s in ("marketplace", "portfolio", "workspace")}


_hub: ToolHub | None = None


def get_hub() -> ToolHub:
    global _hub
    if _hub is None:
        _hub = ToolHub()
    return _hub
