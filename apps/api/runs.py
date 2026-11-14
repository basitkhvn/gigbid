"""Run manager: starts/resumes LangGraph threads in the background, persists node events (for SSE + refresh safety)."""
from __future__ import annotations

import asyncio
import json
import uuid

from langgraph.types import Command

from agent.graphs.bid_graph import build_bid_graph
from agent.graphs.conversation_graph import build_conversation_graph
from agent.tracing import new_trace_id
from apps.api.db import db, get_settings, now, one

GRAPHS: dict = {}
TASKS: dict[str, asyncio.Task] = {}


def graphs(cp):
    GRAPHS["bid"], GRAPHS["conv"] = build_bid_graph(cp), build_conversation_graph(cp)


def _event(run_id: str, node: str, data: dict) -> None:
    db().execute("INSERT INTO run_events(run_id,ts,node,data) VALUES (?,?,?,?)", (run_id, now(), node, json.dumps(data, default=str)[:20000]))


def _set(run_id: str, **kw):
    kw["updated"] = now()
    db().execute(f"UPDATE runs SET {', '.join(k + '=?' for k in kw)} WHERE id=?", (*kw.values(), run_id))


def run_id_for(kind: str, user_id: str, key: str) -> str:
    return f"{kind}:{user_id}:{key}"


async def _drive(run_id: str, kind: str, payload, cfg):
    g = GRAPHS[kind]
    try:
        async for chunk in g.astream(payload, cfg, stream_mode="updates"):
            for node, upd in chunk.items():
                if node == "__interrupt__":
                    continue
                keys = list((upd or {}).keys()) if isinstance(upd, dict) else []
                _event(run_id, node, {"keys": keys, "status": (upd or {}).get("status") if isinstance(upd, dict) else None,
                                      "summary": _summ(node, upd)})
        st = await g.aget_state(cfg)
        status = st.values.get("status", "done")
        if st.next:  # paused at an interrupt
            status = "awaiting_approval"
        _set(run_id, status=status, summary=json.dumps({**_final_summary(st.values), "thread": cfg["configurable"]["thread_id"]}, default=str))  # keep the thread id: re-runs use a suffixed thread, and approvals are looked up through it
        _event(run_id, "__end__", {"status": status})
    except Exception as e:  # noqa: BLE001
        _set(run_id, status="needs_attention")
        _event(run_id, "__error__", {"error": repr(e)})


def _summ(node, upd):
    if not isinstance(upd, dict):
        return ""
    if node == "risk_assessor" and "risk_report" in upd:
        r = upd["risk_report"]; return f"risk {r['score']} flags={r['flags']}"
    if node == "fit_matcher" and "fit_report" in upd:
        return f"fit {upd['fit_report']['score']}"
    if node == "decide":
        return f"{upd['decision']['action']}: {'; '.join(upd['decision']['reasons'][:2])}"
    if node == "critic":
        c = upd["critiques"][-1]; return f"ok={c['ok']} issues={c['issues']}"
    if node == "compliance":
        return f"passed={upd['compliance']['passed']} violations={upd['compliance']['violations']}"
    if node == "verifier":
        s = upd["claim_stats"]; return f"unsupported {s['unsupported_before']}->{s['unsupported_after']} of {s['claims_before']} claims"
    if node == "executor":
        return f"submitted: {upd.get('submission', {}).get('status')}"
    return ""


def _final_summary(v: dict) -> dict:
    return {"decision": v.get("decision"), "fit": (v.get("fit_report") or {}).get("score"), "risk": (v.get("risk_report") or {}).get("score"),
            "flags": (v.get("risk_report") or {}).get("flags"), "bid": (v.get("price_quote") or {}).get("bid"),
            "connects": (v.get("price_quote") or {}).get("connects_cost"), "claim_stats": v.get("claim_stats"),
            "submission": v.get("submission")}


def start_bid(user: dict, job: dict) -> str:
    rid = run_id_for("bid", user["id"], job["job_id"])
    existing = one("SELECT status FROM runs WHERE id=? AND user_id=?", rid, user["id"])
    if existing and existing["status"] not in ("queued_unavailable", "dead_letter", "needs_attention"):
        return rid  # idempotent: one thread per job
    tid = new_trace_id()
    db().execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 (rid, user["id"], "bid", job["job_id"], "", tid, "running", job.get("category", ""), job["title"], now(), now(), "{}"))
    st = get_settings(user["id"])
    cfg = {"configurable": {"thread_id": rid + (":" + uuid.uuid4().hex[:4] if existing else "")}}
    db().execute("UPDATE runs SET summary=? WHERE id=?", (json.dumps({"thread": cfg["configurable"]["thread_id"]}), rid))
    payload = {"user_id": user["id"], "persona": user["persona"], "job_id": job["job_id"], "profile": st, "trace_id": tid}
    TASKS[rid] = asyncio.create_task(_drive(rid, "bid", payload, cfg))
    return rid


def thread_of(run_id: str) -> str:
    r = one("SELECT summary FROM runs WHERE id=?", run_id)
    try:
        return json.loads(r["summary"]).get("thread") or run_id
    except Exception:  # noqa: BLE001
        return run_id


def cfg_of(run_id: str) -> dict:
    return {"configurable": {"thread_id": thread_of(run_id)}}


def resume(run_id: str, kind: str, decision: dict) -> None:
    _set(run_id, status="running")
    _event(run_id, "__resume__", {"action": decision.get("action")})
    TASKS[run_id] = asyncio.create_task(_drive(run_id, kind, Command(resume=decision), cfg_of(run_id)))


def start_conversation(user: dict, proposal_id: str) -> str:
    rid = run_id_for("conv", user["id"], proposal_id)
    tid = new_trace_id()
    ex = one("SELECT id FROM runs WHERE id=?", rid)
    thread = rid + ":" + uuid.uuid4().hex[:4]
    if ex:
        db().execute("DELETE FROM runs WHERE id=?", (rid,))
    db().execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 (rid, user["id"], "conv", "", proposal_id, tid, "running", "", f"Conversation {proposal_id}", now(), now(),
                  json.dumps({"thread": thread})))
    cfg = {"configurable": {"thread_id": thread}}
    payload = {"user_id": user["id"], "persona": user["persona"], "proposal_id": proposal_id, "trace_id": tid}
    TASKS[rid] = asyncio.create_task(_drive(rid, "conv", payload, cfg))
    return rid
