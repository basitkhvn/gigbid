from __future__ import annotations

import re

from agent.guard import detect_injection, wrap_untrusted
from agent.handoffs import ConversationReply
from agent.llm import complete_json, prompt
from agent.mcp_client import get_hub
from agent.nodes.common import node

INTENT_RULES = [("scam_signal", r"telegram|whatsapp|crypto|outside the platform|send (me )?your (password|credentials)|gift card"),
                ("interview_request", r"interview|call|meet|schedule|available"),
                ("negotiation", r"rate|budget|price|discount|cheaper|lower|cost")]


def classify_rule(text: str) -> str:
    for intent, rx in INTENT_RULES:
        if re.search(rx, text, re.I):
            return intent
    return "question"


@node("client_liaison")
async def liaison_draft(state):
    msgs = state["messages"]
    last = next((m for m in reversed(msgs) if m["from"] == "client"), None)
    if not last:
        return {"status": "nothing_to_do"}
    text = last["text"]
    intent = classify_rule(text)
    slots: list[str] = []
    if intent == "interview_request":
        s = await get_hub().call("client_liaison", "free_slots", {"user_id": state["user_id"], "days": 5})
        slots = s["slots"][:3]
    ev = []
    if intent in ("question", "negotiation"):
        ev = await get_hub().call("client_liaison", "search_evidence", {"requirement": text[:200], "k": 2, "persona": state["persona"]})
    llm = complete_json("client_liaison", prompt("client_liaison"),
                        f"{wrap_untrusted(text, 'client_message')}\nEVIDENCE: {[e['snippet'] for e in ev]}\nSLOTS: {slots}")
    if llm and llm.get("reply") and intent != "scam_signal":
        intent = llm.get("intent") if llm.get("intent") in ("question", "negotiation", "interview_request", "scam_signal") else intent
        reply = str(llm["reply"])
    else:
        reply = {"scam_signal": "I keep all communication and payment on the platform, so I will not continue off-platform. Thank you for understanding.",
                 "interview_request": "Thank you! I would be happy to talk. These slots work for me: " + "; ".join(slots) + ".",
                 "negotiation": "Thanks for the details. I can work within a scoped milestone plan; happy to discuss options on the platform.",
                 "question": "Thanks for the question. I have delivered similar work and will happily share specifics on the platform."}[intent]
    flags = (["injection"] if detect_injection(text) else []) + (["scam_signal"] if intent == "scam_signal" else [])
    r = ConversationReply(intent=intent, reply=reply, slots=slots)
    return {"intent": intent, "reply": r.model_dump(), "risk_flags": flags}
