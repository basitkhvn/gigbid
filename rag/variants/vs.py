"""Variants V0-V8. Each: fn(corpus, job, k, **opts) -> list[evidence dict]. See rag/retriever.py."""
from __future__ import annotations

from agent.llm import complete, is_offline, prompt
from rag.corpus import OUTCOME_W, Corpus
from rag.index.stores import rerank
from rag.requirements import extract
from rag.variants.base import job_query, minmax, rrf, to_evidence


def _dense_scored(idx, q, n=30):
    return [(idx.chunks[i], s) for i, s in idx.dense(q, n)]


def v0_naive(c: Corpus, job, k=5, **_):
    """Baseline: fixed chunks, top-k cosine on the whole job post."""
    return to_evidence(c, _dense_scored(c.plain, job_query(job)), k, "v0")


def _decomposed(c: Corpus, job, k, per_req_fn, use_llm=False):
    reqs = extract(job, use_llm)
    agg: dict[str, tuple[dict, float]] = {}
    for rq in reqs:
        for ch, s in per_req_fn(rq):
            # merge: best score per chunk across requirements, plus coverage bonus for multi-hit items
            prev = agg.get(ch["chunk_id"])
            agg[ch["chunk_id"]] = (ch, (prev[1] if prev else 0) + s)
    return to_evidence(c, list(agg.values()), k)


def v1_decompose(c: Corpus, job, k=5, use_llm=False, **_):
    ev = _decomposed(c, job, k, lambda rq: _dense_scored(c.plain, rq, 10), use_llm)
    return [{**e, "via": "v1"} for e in ev]


def _hybrid(c: Corpus, idx, q, n=30):
    d = [i for i, _ in idx.dense(q, n)]
    s = [i for i, _ in idx.sparse(q, n)]
    sc = rrf([d, s])
    return [(idx.chunks[i], v) for i, v in sc.items()]


def v2_hybrid(c: Corpus, job, k=5, **_):
    return to_evidence(c, _hybrid(c, c.plain, job_query(job)), k, "v2")


def v3_rerank(c: Corpus, job, k=5, base="v2", use_llm=False, **_):
    cand = to_evidence(c, _hybrid(c, c.plain, job_query(job), 40), 25, "v3")
    reqs = extract(job, use_llm)
    # cross-encoder scores each candidate against each requirement; item score = sum of best matches
    scores = [0.0] * len(cand)
    for rq in reqs:
        rs = rerank(rq, [e["text"] for e in cand])
        for i, s in enumerate(minmax(rs)):
            scores[i] += s
    for e, s in zip(cand, scores):
        e["score"] = round(float(s), 5)
    return sorted(cand, key=lambda e: -e["score"])[:k]


def _prior(c: Corpus, e) -> float:
    if e["type"] == "proposal":
        return OUTCOME_W.get(e.get("outcome") or "ignored", 0.0)
    return c.project_outcome.get(e.get("project"), 0.0)


def v4_outcome(c: Corpus, job, k=5, lam=0.6, **_):
    """Outcome-aware: boost evidence from projects/proposals that won or got replies."""
    cand = to_evidence(c, _hybrid(c, c.plain, job_query(job), 40), 30, "v4")
    for e in cand:
        e["score"] = round(e["score"] * (1 + lam * _prior(c, e)), 6)
    return sorted(cand, key=lambda e: -e["score"])[:k]


def v5_multivector(c: Corpus, job, k=5, **_):
    """Case study / README / review of a project indexed separately, merged into one project item."""
    reqs = extract(job)
    proj: dict[str, float] = {}
    for rq in reqs:
        for i, s in c.multivector.dense(rq, 15):
            p = c.multivector.chunks[i]["project"]
            proj[p] = proj.get(p, 0) + s
    out = []
    for p, s in sorted(proj.items(), key=lambda x: -x[1])[:k]:
        it = c.by_id[f"{p}-case"]
        out.append({"id": it["id"], "type": "case_study", "project": p, "title": it["title"], "source": it["id"],
                    "date": it["date"], "outcome": None, "industry": it["industry"], "skills": it["skills"],
                    "score": round(s, 5), "text": it["text"], "via": "v5"})
    return out


def v6_contextual(c: Corpus, job, k=5, **_):
    idx = c.contextual
    return to_evidence(c, _hybrid(c, idx, job_query(job)), k, "v6")


def v7_hyde(c: Corpus, job, k=5, **_):
    hypo = None
    if not is_offline("writer"):
        r = complete("analyst", prompt("hyde"), f"<job_post>{job_query(job)}</job_post>")
        hypo = r.text if r else None
    if not hypo:  # offline template hypothetical proposal
        hypo = "I have delivered similar projects using " + ", ".join(extract(job)) + ". " + job.get("description", "")[:200]
    return to_evidence(c, _hybrid(c, c.plain, hypo), k, "v7")


def v8_corrective(c: Corpus, job, k=5, min_rerank=-4.0, **_):
    """Corrective RAG: retrieve per requirement, grade with the cross-encoder, re-query with a rewritten query
    when weak, and REFUSE (mark unsupported) when still nothing. Runs as a LangGraph loop in rag/corrective.py."""
    from rag.corrective import run_corrective
    return run_corrective(c, job, k, min_rerank)


def v_best(c: Corpus, job, k=5, types=None, decompose=True, hybrid=True, rerank_on=True, outcome=True, **_):
    """Final pipeline: decomposition + hybrid(BM25+dense, RRF) + cross-encoder rerank + outcome-aware boost.
    Each component can be switched off for the one-at-a-time ablation (evals/runners/ablation.py)."""
    reqs = extract(job) if decompose else [job_query(job)]
    pool: dict[str, tuple[dict, float]] = {}
    for rq in reqs:
        n = 60 if types else 15
        cands = _hybrid(c, c.plain, rq, n) if hybrid else _dense_scored(c.plain, rq, n)
        for ch, sc in cands:
            if types and ch["type"] not in types:
                continue
            if ch["chunk_id"] not in pool or sc > pool[ch["chunk_id"]][1]:
                pool[ch["chunk_id"]] = (ch, sc)
    cand = to_evidence(c, list(pool.values()), 25, "best")
    scores = [0.0] * len(cand)
    raw = [-99.0] * len(cand)
    if rerank_on:
        for rq in reqs:
            rr = rerank(rq, [e["text"][:1500] for e in cand])
            for i, sc in enumerate(minmax(rr)):
                scores[i] += sc
                raw[i] = max(raw[i], float(rr[i]))
    else:
        scores = [e["score"] for e in cand]
    for e, sc, rw in zip(cand, scores, raw):
        e["score"] = round(float(sc) * (1 + (0.3 * _prior(c, e) if outcome else 0)), 5)
        e["relevance"] = round(rw, 3) if rerank_on else None
    return sorted(cand, key=lambda e: -e["score"])[:k]
