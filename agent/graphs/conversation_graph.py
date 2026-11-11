"""Conversation graph (one thread per client conversation): read -> classify+draft -> approval interrupt -> send."""
from __future__ import annotations

import hashlib

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agent.mcp_client import get_hub
from agent.nodes.client_liaison import liaison_draft
from agent.nodes.common import node
from agent.nodes.compliance import check_text
from agent.state import ConvState


@node("read_messages")
async def read_messages(state: ConvState):
    r = await get_hub().call("client_liaison", "list_messages", {"user_id": state["user_id"], "proposal_id": state["proposal_id"]})
    return {"messages": r["messages"]}


@node("conv_approval")
async def conv_approval(state: ConvState):
    rep = state["reply"]
    v = check_text(rep["reply"], {"flags": []})
    decision = interrupt({"type": "message_approval", "proposal_id": state["proposal_id"], "intent": state["intent"],
                          "reply": {**rep, "reply": v.sanitized_text}, "risk_flags": state.get("risk_flags", []), "slots": rep["slots"]})
    return {"approval": decision, "status": "awaiting_approval"}


def after_draft(state: ConvState):
    return END if state.get("status") == "nothing_to_do" else "conv_approval"


def after_conv_approval(state: ConvState):
    return "send" if state["approval"].get("action") in ("approve", "edit") else END


@node("send")
async def send(state: ConvState):
    a, hub = state["approval"], get_hub()
    text = check_text(a.get("text") or state["reply"]["reply"], {"flags": []}).sanitized_text
    key = hashlib.sha1(f"{state['user_id']}:{state['proposal_id']}:{len(state['messages'])}".encode()).hexdigest()[:24]
    res = await hub.call("executor", "send_message", {"inp": {"user_id": state["user_id"], "proposal_id": state["proposal_id"],
                                                              "text": text, "idempotency_key": key}})
    if state["intent"] == "interview_request" and state["reply"].get("slots"):
        await hub.call("client_liaison", "create_interview_hold", {"inp": {"user_id": state["user_id"], "start": state["reply"]["slots"][0],
                                                                         "title": f"Interview {state['proposal_id']}", "idempotency_key": key + "-hold"}})
    return {"sent": res, "status": "sent"}


def build_conversation_graph(checkpointer=None):
    g = StateGraph(ConvState)
    g.add_node("read_messages", read_messages); g.add_node("liaison", liaison_draft)
    g.add_node("conv_approval", conv_approval); g.add_node("send", send)
    g.add_edge(START, "read_messages"); g.add_edge("read_messages", "liaison")
    g.add_conditional_edges("liaison", after_draft, {"conv_approval": "conv_approval", END: END})
    g.add_conditional_edges("conv_approval", after_conv_approval, {"send": "send", END: END})
    g.add_edge("send", END)
    return g.compile(checkpointer=checkpointer)
