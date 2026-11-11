from __future__ import annotations

import re

from agent.config import load_config
from agent.guard import detect_injection, wrap_untrusted
from agent.handoffs import RiskReport
from agent.llm import acomplete_json, prompt
from agent.mcp_client import get_hub
from agent.nodes.common import node

SCAM_RULES = {  # flag -> (regex, weight)
    "unpaid_work": (r"free trial|unpaid|for free|payment only if|complete a full working", 0.6),
    "off_platform_contact": (r"telegram|whatsapp|skype|@[\w-]+\.\w+|\+\d[\d\s-]{7,}|contact me (at|on)|external messaging", 0.6),
    "off_platform_payment": (r"crypto|wallet|bank transfer|outside the platform|direct payment|paypal me", 0.6),
    "guarantee_bait": (r"guarantee 100%|unlimited revisions for a flat|100% results", 0.35),
}


def rule_scan(text: str) -> dict[str, float]:
    return {f: w for f, (rx, w) in SCAM_RULES.items() if re.search(rx, text, re.I)}


@node("risk_assessor")
async def risk_assessor(state):
    job = state["job"]
    text = job["title"] + "\n" + job["description"]
    hits = rule_scan(text)
    b = (job.get("budget") or {}).get("max")
    if b is not None and b < 100:  # fix from failure analysis (17 guarantee-bait scams missed): implausibly low budget signal
        hits["implausibly_low_budget"] = 0.3
    inj = detect_injection(text)
    quality = 0.5
    try:
        c = await get_hub().call("risk_assessor", "get_client_history", {"user_id": state["user_id"], "client_id": job["client_id"]})
        quality = 0.35 * min(1, c["total_spent"] / 25000) + 0.25 * c["hire_rate"] + 0.2 * (c["avg_rating"] - 3) / 2 + 0.2 * (1 if c["payment_verified"] else 0)
    except Exception:  # client history is advisory: absence must not block the run  # noqa: BLE001
        pass
    flags = list(hits)
    llm_expl = ""
    llm = await acomplete_json("risk_assessor", prompt("risk_assessor"), wrap_untrusted(text))
    if llm:  # LLM can add flags the rules miss; it can never remove a rule flag
        for f in llm.get("flags", []):
            if f in ("unpaid_work", "off_platform_contact", "off_platform_payment", "guarantee_bait") and f not in flags:
                flags.append(f); hits[f] = 0.5
        llm_expl = str(llm.get("explanation", ""))
        inj = inj or "injection" in llm.get("flags", [])
    if inj:
        flags.append("injection")
    if quality < 0.35:
        flags.append("low_client_quality")
    scam_score = min(1.0, sum(hits.values()))
    score = min(1.0, scam_score + 0.15 * (1 - quality))
    rep = RiskReport(score=round(score, 3), flags=flags, client_quality=round(quality, 3), injection_detected=inj,
                     explanation=llm_expl or (f"Flags: {', '.join(flags)}" if flags else "No risk signals found."))
    return {"risk_report": rep.model_dump()}
