from __future__ import annotations

import re

from agent.config import load_config
from agent.guard import wrap_untrusted
from agent.handoffs import Critique
from agent.llm import acomplete_json, prompt
from agent.nodes.common import node

GENERIC = ("i am writing to apply", "dear sir", "hardworking", "i am a hard", "passionate", "i can start right away")


def rule_critique(text: str, job: dict, fit: dict) -> Critique:
    issues, words = [], len(text.split())
    if words < 40 or words > 260:
        issues.append(f"length {words} words is outside 40-260")
    if any(g in text.lower() for g in GENERIC):
        issues.append("generic opening/phrase detected")
    if not re.search(r"\[E\d+\]", text):
        issues.append("no evidence citations")
    req = [m["requirement"].lower() for m in fit.get("matches", []) if m["supported"]]
    if req and sum(r in text.lower() for r in req) < max(1, len(req) // 2):
        issues.append("does not address the job's key requirements")
    ok = not issues
    return Critique(ok=ok, score=max(0.0, 1 - 0.25 * len(issues)), issues=issues,
                    revision_instructions="; ".join(issues) and ("Fix: " + "; ".join(issues)))


@node("critic")
async def critic(state):
    text = state["draft"]["cover_letter"]
    c = rule_critique(text, state["job"], state["fit_report"])
    llm = await acomplete_json("critic", prompt("critic"), wrap_untrusted(state["job"]["description"]) + f"\n\nDRAFT:\n{text}")
    if llm:
        c.issues += [str(i) for i in llm.get("issues", []) if str(i) not in c.issues][:3]
        if not llm.get("ok", True):
            c.ok = False
            c.revision_instructions = (c.revision_instructions + " " + str(llm.get("revision_instructions", ""))).strip()
    return {"critiques": [c.model_dump()]}
