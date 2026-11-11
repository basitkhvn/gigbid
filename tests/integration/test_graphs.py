"""Graph runs against the GigSim stand-in (offline model profile)."""

import pytest
from langgraph.types import Command

from agent.checkpointer import make_checkpointer
from agent.graphs.bid_graph import build_bid_graph
from agent.mcp_client import get_hub
from evals.common import dev
from gigsim_local.app import register_jobs

PROF = {"rate": 55, "floor": 35}


def pick(kind, scam=False):
    jobs = dev("ml")
    register_jobs(jobs)
    return next(j for j in jobs if j["gold"]["kind"] == kind and j["gold"]["scam"] == scam and (scam or j["gold"]["bid"]))


def inp(uid, j):
    return {"user_id": uid, "persona": "ml", "profile": PROF, "job_id": j["job_id"], "trace_id": "t-" + uid}


async def balance(uid):
    return (await get_hub().call("ui", "get_connects_balance", {"user_id": uid}))["balance"]


async def test_scam_is_skipped_and_nothing_sent():
    j = pick("scam", scam=True)
    async with make_checkpointer() as cp:
        g = build_bid_graph(cp)
        out = await g.ainvoke(inp("scam-u", j), {"configurable": {"thread_id": "scam-1"}})
        assert out["decision"]["action"] == "skip" and "submission" not in out
        assert not (await g.aget_state({"configurable": {"thread_id": "scam-1"}})).next


async def test_parallel_branches_all_ran_then_pause_for_approval():
    j = pick("good")
    async with make_checkpointer() as cp:
        g = build_bid_graph(cp)
        cfg = {"configurable": {"thread_id": "par-1"}}
        out = await g.ainvoke(inp("par-u", j), cfg)
        assert {"job_spec", "risk_report", "fit_report"} <= set(out)
        assert out["status"] == "awaiting_approval"
        assert (await g.aget_state(cfg)).next == ("approval",)
        assert await balance("par-u") == 100000  # nothing spent before approval


async def test_reject_never_submits_and_edit_goes_through_compliance():
    j = pick("good")
    async with make_checkpointer() as cp:
        g = build_bid_graph(cp)
        c1 = {"configurable": {"thread_id": "rej-1"}}
        await g.ainvoke(inp("rej-u", j), c1)
        out = await g.ainvoke(Command(resume={"action": "reject", "reason": "too generic"}), c1)
        assert out["status"] == "rejected" and "submission" not in out
        c2 = {"configurable": {"thread_id": "edit-1"}}
        await g.ainvoke(inp("edit-u", j), c2)
        out = await g.ainvoke(Command(resume={"action": "edit", "text": "Message me on WhatsApp, I guarantee 100% success."}), c2)
        assert out["status"] != "submitted"  # compliance failed the edit; loops back for another human decision
        assert (await g.aget_state(c2)).next


async def test_crash_and_resume_submits_exactly_once(tmp_path):
    """Kill the API (new graph + new checkpointer connection) while a proposal waits; approve; submitted exactly once."""
    j = pick("good")
    cfg = {"configurable": {"thread_id": "crash-1"}}
    async with make_checkpointer() as cp:
        await build_bid_graph(cp).ainvoke(inp("crash-u", j), cfg)
    # ---- 'restart': fresh graph object and fresh DB connection
    async with make_checkpointer() as cp2:
        g2 = build_bid_graph(cp2)
        assert (await g2.aget_state(cfg)).next == ("approval",)  # pending approval survived
        out = await g2.ainvoke(Command(resume={"action": "approve"}), cfg)
        assert out["status"] == "submitted"
        spent = 100000 - await balance("crash-u")
        assert spent == out["submission"]["connects_spent"] > 0
        # replaying the executor from the checkpoint history must NOT spend again
        hist = [s async for s in g2.aget_state_history(cfg)]
        before_exec = next(s for s in hist if s.next == ("executor",))
        await g2.ainvoke(None, before_exec.config)
        assert 100000 - await balance("crash-u") == spent


async def test_marketplace_outage_queues_work_instead_of_crashing():
    j = pick("good")
    hub = get_hub()
    hub.disabled.add("marketplace")
    try:
        async with make_checkpointer() as cp:
            g = build_bid_graph(cp)
            out = await g.ainvoke({**inp("out-u", j), "job": {k: v for k, v in j.items() if k != "gold"}}, {"configurable": {"thread_id": "out-1"}})
            assert out["status"] == "queued_unavailable" or out.get("degraded")
        assert hub.status()["marketplace"]["ok"] is False
    finally:
        hub.disabled.discard("marketplace")


async def test_allowlist_blocks_unauthorised_tool():
    from agent.mcp_client import ToolNotAllowed
    with pytest.raises(ToolNotAllowed):
        await get_hub().call("writer", "submit_proposal", {})
    with pytest.raises(ToolNotAllowed):
        await get_hub().call("risk_assessor", "send_message", {})
