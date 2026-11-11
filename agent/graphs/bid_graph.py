"""Bid graph (one thread per job). Hand-written StateGraph; analyst/risk/fit run in PARALLEL via Send; a decision
node chooses skip|watch|bid; pricing -> writer -> verifier -> critic (<=2 loops) -> compliance; then a human approval
interrupt() before ANYTHING is sent (R4). The executor runs only after approval and is idempotent (exactly once)."""
from __future__ import annotations

import difflib
import hashlib

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt

from agent.config import load_config
from agent.mcp_client import ToolUnavailable, get_hub
from agent.memory import promotion_rules as mem
from agent.nodes.analyst import analyst
from agent.nodes.common import node
from agent.nodes.compliance import check_text, compliance
from agent.nodes.critic import critic
from agent.nodes.fit_matcher import fit_matcher
from agent.nodes.pricing import pricing
from agent.nodes.risk_assessor import risk_assessor
from agent.nodes.scout import scout
from agent.nodes.verifier import verifier
from agent.nodes.writer import writer
from agent.state import BidState


def fan_out(state: BidState):
    if state.get("duplicate") or state.get("status") in ("queued_unavailable", "dead_letter", "needs_attention"):
        return END
    return [Send("analyst", state), Send("risk_assessor", state), Send("fit_matcher", state)]


@node("decide")
async def decide(state: BidState):
    t = load_config()["thresholds"]
    fit, risk = state["fit_report"], state["risk_report"]
    prof = state.get("profile", {})
    reasons = [f"fit {fit['score']:.2f} (min {t['minimum_fit_score']})", f"risk {risk['score']:.2f} (max {t['maximum_risk_score']})"]
    if risk["score"] >= t["maximum_risk_score"]:
        action, reasons = "skip", reasons + [f"risk flags: {', '.join(risk['flags'])}"]
    elif fit["score"] >= t["minimum_fit_score"]:
        action = "bid"
    elif fit["score"] >= 0.4:
        action, reasons = "watch", reasons + ["partial fit: worth watching, not bidding"]
    else:
        action, reasons = "skip", reasons + fit["reasons"][1:3]
    auto = action == "skip" and prof.get("autonomy") == "auto_skip" and fit["score"] < t.get("autonomy_skip_below_fit", 0.3)
    return {"decision": {"action": action, "reasons": reasons, "auto": auto},
            "status": {"skip": "skipped", "watch": "watching", "bid": "bidding"}[action]}


FAILED = ("queued_unavailable", "dead_letter", "needs_attention")


def after_decide(state: BidState):
    if state.get("status") in FAILED:
        return END
    return "pricing" if state["decision"]["action"] == "bid" else END


def after_critic(state: BidState):
    if state.get("status") in FAILED or not state.get("critiques"):
        return END
    max_rev = load_config()["budgets"]["max_revisions"]
    last = state["critiques"][-1]
    if not last["ok"] and state.get("revisions", 0) < max_rev:
        return "writer"
    return "compliance"


def after_compliance(state: BidState):
    if state.get("status") in FAILED:
        return END
    return END if state["compliance"]["blocked"] else "prepare_approval"


@node("prepare_approval")
async def prepare_approval(state: BidState):
    """Builds everything the human needs to decide, incl. the dry_run preview of what will be sent and its cost."""
    draft, q = state["draft"], state["price_quote"]
    ev = {e["id"]: e for e in state.get("evidence", [])}
    key = idem_key(state, "draft")
    preview = await get_hub().call("executor", "create_proposal_draft", {"inp": {
        "user_id": state["user_id"], "job_id": state["job_id"], "cover_letter": draft["cover_letter"] or "x" * 20,
        "bid": q["bid"], "idempotency_key": key + "-preview", "dry_run": True}})
    return {"preview": preview, "status": "awaiting_approval"}


def idem_key(state: BidState, what: str) -> str:
    return hashlib.sha1(f"{state['user_id']}:{state['job_id']}:{what}".encode()).hexdigest()[:24]


@node("approval")
async def approval(state: BidState):
    payload = {"type": "proposal_approval", "job_id": state["job_id"], "draft": state["draft"],
               "evidence": state.get("evidence", []), "risk_report": state["risk_report"], "price_quote": state["price_quote"],
               "preview": state.get("preview"), "compliance": state.get("compliance"), "claim_stats": state.get("claim_stats")}
    decision = interrupt(payload)          # <- graph pauses here; state is checkpointed; resumes via Command(resume=...)
    return {"approval": decision}


def after_approval(state: BidState):
    a = state["approval"]
    return {"approve": "executor", "edit": "recheck_edit", "reject": "rejected"}.get(a.get("action"), "rejected")


@node("recheck_edit")
async def recheck_edit(state: BidState):
    a = state["approval"]
    orig, edited = state["draft"]["cover_letter"], a.get("text", "")
    v = check_text(edited, state.get("risk_report"))
    promoted = mem.record_edit(state["user_id"], state["job_id"], orig, edited)  # style memory via promotion rule
    diff = "\n".join(difflib.unified_diff(orig.split(". "), edited.split(". "), lineterm="", n=0))
    out = {"approval": {**a, "diff": diff, "promoted_rules": promoted, "recheck": v.model_dump()}}
    if v.passed:
        out["draft"] = {**state["draft"], "cover_letter": v.sanitized_text}
        out["compliance"] = v.model_dump()
    else:
        out["compliance"] = v.model_dump()
        out["status"] = "edit_failed_compliance"
    return out


def after_recheck(state: BidState):
    return "executor" if state["compliance"]["passed"] else "prepare_approval"


@node("rejected")
async def rejected(state: BidState):
    return {"status": "rejected", "outcome": {"rejected_reason": state["approval"].get("reason", "")}}


@node("executor")
async def executor(state: BidState):
    """Runs only after a human approved. Idempotency keys are deterministic per (user, job): a crash/retry after the
    submit call returns the first result and never spends Connects twice."""
    hub, draft, q = get_hub(), state["draft"], state["price_quote"]
    d = await hub.call("executor", "create_proposal_draft", {"inp": {
        "user_id": state["user_id"], "job_id": state["job_id"], "cover_letter": draft["cover_letter"], "bid": q["bid"],
        "screening_answers": draft.get("screening_answers", []), "idempotency_key": idem_key(state, "draft"), "dry_run": False}})
    res = await hub.call("executor", "submit_proposal", {"inp": {
        "user_id": state["user_id"], "draft_id": d["draft_id"], "idempotency_key": idem_key(state, "submit")}})
    return {"submission": res, "status": "submitted"}


def build_bid_graph(checkpointer=None):
    g = StateGraph(BidState)
    for name, fn in [("scout", scout), ("analyst", analyst), ("risk_assessor", risk_assessor), ("fit_matcher", fit_matcher),
                     ("decide", decide), ("pricing", pricing), ("writer", writer), ("verifier", verifier), ("critic", critic),
                     ("compliance", compliance), ("prepare_approval", prepare_approval), ("approval", approval),
                     ("recheck_edit", recheck_edit), ("rejected", rejected), ("executor", executor)]:
        g.add_node(name, fn)
    g.add_edge(START, "scout")
    g.add_conditional_edges("scout", fan_out, ["analyst", "risk_assessor", "fit_matcher", END])
    for n in ("analyst", "risk_assessor", "fit_matcher"):
        g.add_edge(n, "decide")
    g.add_conditional_edges("decide", after_decide, {"pricing": "pricing", END: END})
    g.add_edge("pricing", "writer"); g.add_edge("writer", "verifier"); g.add_edge("verifier", "critic")
    g.add_conditional_edges("critic", after_critic, {"writer": "writer", "compliance": "compliance", END: END})
    g.add_conditional_edges("compliance", after_compliance, {"prepare_approval": "prepare_approval", END: END})
    g.add_edge("prepare_approval", "approval")
    g.add_conditional_edges("approval", after_approval, {"executor": "executor", "recheck_edit": "recheck_edit", "rejected": "rejected"})
    g.add_conditional_edges("recheck_edit", after_recheck, {"executor": "executor", "prepare_approval": "prepare_approval"})
    g.add_edge("rejected", END); g.add_edge("executor", END)
    return g.compile(checkpointer=checkpointer)
