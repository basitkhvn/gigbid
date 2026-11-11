from __future__ import annotations

from agent.config import load_config
from agent.guard import sanitize
from agent.handoffs import FitReport, RequirementMatch
from agent.mcp_client import get_hub
from agent.nodes.common import node
from rag.requirements import extract


@node("fit_matcher")
async def fit_matcher(state):
    job = state["job"]
    reqs = extract({"title": job["title"], "description": sanitize(job["description"])})[:8]
    tau = load_config()["thresholds"]["fit_support_relevance"]
    matches, evidence, seen = [], [], set()
    for rq in reqs:
        res = await get_hub().call("fit_matcher", "search_evidence", {"requirement": rq, "k": 5, "persona": state["persona"], "filters": {"types": ["case_study", "readme", "review", "cv"]}})
        # past proposals are unverified marketing text: they inform style/outcome ranking, never prove experience
        res = [e for e in res if e["type"] != "proposal"]
        res = sorted(res, key=lambda e: (e["type"] not in ("case_study", "readme"), -(e.get("relevance") or -99)))
        best = max((e.get("relevance") or -99 for e in res), default=-99)
        sup = best >= tau
        matches.append(RequirementMatch(requirement=rq, supported=sup, evidence_ids=[e["id"] for e in res[:2]] if sup else [], best_score=best))
        if sup:
            for e in res[:2]:
                if e["id"] not in seen:
                    seen.add(e["id"]); evidence.append({**e, "text": e.get("snippet", "")})
    n_sup = sum(m.supported for m in matches)
    score = n_sup / max(1, len(matches))
    rep = FitReport(score=round(score, 3), matches=matches, matched_skills=[m.requirement for m in matches if m.supported],
                    missing_skills=[m.requirement for m in matches if not m.supported], evidence_ids=[e["id"] for e in evidence],
                    reasons=[f"{n_sup}/{len(matches)} requirements have portfolio evidence"] +
                            [f"no evidence for: {m.requirement}" for m in matches if not m.supported])
    return {"fit_report": rep.model_dump(), "evidence": evidence}
