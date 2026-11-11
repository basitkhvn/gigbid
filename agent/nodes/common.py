"""Node wrapper: step counting, tracing span, budgets, per-node retry/timeout, degraded handling (C4, C7)."""
from __future__ import annotations

import asyncio
import functools

from langgraph.errors import GraphBubbleUp

from agent.config import load_config
from agent.mcp_client import ToolUnavailable
from agent.tracing import set_trace, span, summarize


def node(name: str, timeout_s: float = 90, retries: int = 1):
    def deco(fn):
        @functools.wraps(fn)
        async def wrapper(state):
            cfg = load_config()["budgets"]
            if state.get("steps", 0) >= cfg["max_graph_steps"]:
                return {"status": "needs_attention", "errors": [f"{name}: step budget exceeded"]}
            tid = state.get("trace_id", "")
            if tid:
                set_trace(tid)
            if tid and summarize(tid)["tokens_in"] + summarize(tid)["tokens_out"] > cfg["max_tokens_per_job"] * 4:
                return {"status": "needs_attention", "errors": [f"{name}: token budget exceeded"]}
            last = None
            for attempt in range(retries + 1):
                with span(name, kind="node", attempt=attempt, job_id=state.get("job_id")) as sp:
                    try:
                        out = await asyncio.wait_for(fn(state), timeout_s)
                        out = dict(out or {})
                        out["steps"] = 1
                        out["log"] = [{"node": name, "ok": True, "keys": [k for k in out if k not in ("steps", "log")]}]
                        return out
                    except GraphBubbleUp:  # interrupt() / control flow must propagate
                        raise
                    except ToolUnavailable as e:  # marketplace/portfolio down: queue, do not crash (degraded mode)
                        sp["degraded"] = str(e)
                        return {"status": "queued_unavailable", "steps": 1, "errors": [f"{name}: {e}"],
                                "degraded": {"reason": str(e)}, "log": [{"node": name, "ok": False, "degraded": str(e)}]}
                    except Exception as e:  # noqa: BLE001
                        last = e
            return {"status": "dead_letter", "steps": 1, "errors": [f"{name}: {last!r}"],
                    "log": [{"node": name, "ok": False, "error": repr(last)}]}
        return wrapper
    return deco
