"""Compliance Guard: enforces the policy pack (rules live in agent/config.yaml platform_rules, prompts in files)."""
from __future__ import annotations

import os
import re

from agent.config import load_config
from agent.handoffs import ComplianceVerdict
from agent.nodes.common import node


def check_text(text: str, risk: dict | None = None) -> ComplianceVerdict:
    rules = load_config()["platform_rules"]
    if os.environ.get("GIGBID_OUTPUT_DEFENCE", "1") == "0":  # evaluation switch only
        return ComplianceVerdict(passed=True, sanitized_text=text)
    viol, kept = [], []
    for sent in re.split(r"(?<=[.!?])\s+", text.strip()):
        low = sent.lower()
        bad = [b for b in rules["banned_phrases"] if b in low]
        contact = [p for p in rules["contact_patterns"] if re.search(p, low)]
        if bad or contact:
            viol += [f"banned phrase '{b}'" for b in bad] + [f"contact/off-platform '{c}'" for c in contact]
            continue
        kept.append(sent)
    clean = " ".join(kept)
    if len(clean) > rules["max_cover_letter_chars"]:
        viol.append(f"too long (> {rules['max_cover_letter_chars']} chars)")
        clean = clean[: rules["max_cover_letter_chars"]].rsplit(" ", 1)[0]
    if len(clean) < rules.get("min_cover_letter_chars", 0):
        viol.append(f"too short (< {rules['min_cover_letter_chars']} chars)")
    blocked = bool(risk and set(risk.get("flags", [])) & {"unpaid_work", "off_platform_contact", "off_platform_payment"})
    still_bad = len(clean) < rules.get("min_cover_letter_chars", 0) or not clean
    return ComplianceVerdict(passed=not blocked and not still_bad, blocked=blocked or still_bad, violations=viol,
                             sanitized_text=clean,
                             reason=("job violates marketplace rules (off-platform/unpaid work)" if blocked else
                                     "nothing left after removing violations" if still_bad else ""))


@node("compliance")
async def compliance(state):
    v = check_text(state["draft"]["cover_letter"], state.get("risk_report"))
    draft = {**state["draft"], "cover_letter": v.sanitized_text}
    return {"compliance": v.model_dump(), "draft": draft, "status": "blocked_by_compliance" if v.blocked else "drafted"}
