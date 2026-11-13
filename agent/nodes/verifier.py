"""Claim verification between Writer and Critic (R5, B3). Records unsupported-claim counts before and after."""
from __future__ import annotations

import os

from agent.handoffs import Claim
from agent.nodes.common import node
from rag.verify import llm_recheck, repair, unsupported_rate, verify


@node("verifier")
async def verifier(state):
    draft, ev = state["draft"], state.get("evidence", [])
    import asyncio
    res = await asyncio.to_thread(lambda: llm_recheck(verify(draft["cover_letter"], ev), ev))
    bad_before, n = unsupported_rate(res)
    # F3 fix: GIGBID_REPAIR_MODE=rewrite rewrites unsupported sentences from the cited evidence; "delete" is the original behaviour (kept for A/B measurement)
    fixed = repair(draft["cover_letter"], res, ev if os.environ.get("GIGBID_REPAIR_MODE", "delete") == "rewrite" else None)
    res2 = verify(fixed, ev) if fixed else []
    bad_after, n_after = unsupported_rate(res2)
    claims = [Claim(text=r["claim"], verdict=r["verdict"], evidence_ids=r["cited"]).model_dump() for r in res2]
    draft = {**draft, "cover_letter": fixed, "claims": claims}
    stats = {"claims_before": n, "unsupported_before": bad_before, "claims_after": n_after, "unsupported_after": bad_after,
             "removed": [r["claim"] for r in res if r["verdict"] in ("unsupported", "partial")]}
    return {"draft": draft, "claim_stats": stats}
