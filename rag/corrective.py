"""V8: Corrective RAG as a LangGraph loop: retrieve -> grade -> (rewrite -> retrieve)* -> finish. Max 2 rewrites."""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from rag.index.stores import rerank
from rag.requirements import extract
from rag.variants.base import to_evidence


class CState(TypedDict, total=False):
    reqs: list[str]
    queries: dict[str, str]
    found: dict[str, list[dict]]
    weak: list[str]
    refused: list[str]
    tries: int


def run_corrective(corpus, job, k, min_rerank):
    from rag.variants.vs import _hybrid

    def retrieve(s: CState):
        found = dict(s.get("found", {}))
        for rq in s["weak"] if s.get("tries", 0) else s["reqs"]:
            ev = to_evidence(corpus, _hybrid(corpus, corpus.plain, s["queries"][rq], 15), 6, "v8")
            sc = rerank(rq, [e["text"] for e in ev])
            for e, x in zip(ev, sc):
                e["score"] = round(x, 4)
            found[rq] = sorted(ev, key=lambda e: -e["score"])
        return {"found": found}

    def grade(s: CState):
        weak = [rq for rq in s["reqs"] if not s["found"].get(rq) or s["found"][rq][0]["score"] < min_rerank]
        return {"weak": weak, "tries": s.get("tries", 0) + 1}

    def rewrite(s: CState):
        q = dict(s["queries"])
        for rq in s["weak"]:
            q[rq] = f"{rq} project delivered for a client {rq} experience"
        return {"queries": q}

    def route(s: CState):
        return "rewrite" if s["weak"] and s["tries"] <= 2 else "finish"

    def finish(s: CState):
        return {"refused": list(s["weak"])}

    g = StateGraph(CState)
    g.add_node("retrieve", retrieve); g.add_node("grade", grade); g.add_node("rewrite", rewrite); g.add_node("finish", finish)
    g.add_edge(START, "retrieve"); g.add_edge("retrieve", "grade")
    g.add_conditional_edges("grade", route, {"rewrite": "rewrite", "finish": "finish"})
    g.add_edge("rewrite", "retrieve"); g.add_edge("finish", END)
    reqs = extract(job)
    out = g.compile().invoke({"reqs": reqs, "queries": {r: r for r in reqs}, "found": {}, "tries": 0})
    # items for requirements judged supported; weak requirements contribute nothing (refuse to claim)
    pool: dict[str, dict] = {}
    for rq in reqs:
        if rq in out["refused"]:
            continue
        for e in out["found"][rq][:3]:
            if e["id"] not in pool or e["score"] > pool[e["id"]]["score"]:
                pool[e["id"]] = e
    res = sorted(pool.values(), key=lambda e: -e["score"])[:k]
    for e in res:
        e["refused_requirements"] = out["refused"]
    return res
