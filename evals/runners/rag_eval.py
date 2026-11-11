"""B4 retrieval evaluation: Recall@5 / MRR / nDCG@10 per variant x persona x job type, plus latency.
Usage: python -m evals.runners.rag_eval [--n 60]  -> evals/results/rag_results.json (+ .csv)
Gold: projects whose (explicit OR implied) skills overlap the job's requirements (see docs/DATA_CARD.md; synthetic)."""
from __future__ import annotations

import argparse
import csv
import time

from evals.common import PERSONAS, RESULTS, dev, mean, pct, write
from rag.metrics import mrr, ndcg_at, project_ranking, recall_at
from rag.retriever import retrieve

VARIANTS = ["v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v_best"]


def evaluate(variant: str, persona: str, jobs: list[dict], **opts):
    if variant == "v7":  # HyDE makes one LLM call per job: run them concurrently
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(8) as ex:
            return list(ex.map(lambda j: _one(variant, persona, j, opts), jobs))
    return [_one(variant, persona, j, opts) for j in jobs]


def _one(variant, persona, j, opts):
    if True:
        g = j["gold"]["relevant_projects"]
        t = time.time()
        ev = retrieve(persona, j, k=10, variant=variant, **opts)
        lat = time.time() - t
        r = project_ranking(ev)
        return {"job": j["job_id"], "n_req": len(j["required_skills"]), "recall5": recall_at(r, g), "mrr": mrr(r, g),
                "ndcg10": ndcg_at(r, g), "lat": lat}


def summarize(rows):
    multi = [r for r in rows if r["n_req"] >= 4]
    return {"n": len(rows), "recall5": mean(r["recall5"] for r in rows), "mrr": mean(r["mrr"] for r in rows),
            "ndcg10": mean(r["ndcg10"] for r in rows), "p50_latency_s": pct([r["lat"] for r in rows], .5),
            "p95_latency_s": pct([r["lat"] for r in rows], .95),
            "recall5_ge4_reqs": mean(r["recall5"] for r in multi), "n_ge4_reqs": len(multi)}


def jobs_for(persona, n):
    js = [j for j in dev(persona) if j["gold"]["relevant_projects"] and not j["gold"]["scam"]]
    return js[:n]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=60); a = ap.parse_args()
    out = {"n_per_persona": a.n, "note": "rule-based requirement extraction; synthetic gold; see DATA_CARD", "variants": {}}
    for v in VARIANTS:
        out["variants"][v] = {"by_persona": {}}
        allrows = []
        for p in PERSONAS:
            rows = evaluate(v, p, jobs_for(p, a.n))
            out["variants"][v]["by_persona"][p] = summarize(rows)
            allrows += rows
        out["variants"][v]["overall"] = summarize(allrows)
        print(v, out["variants"][v]["overall"], flush=True)
    write("rag_results.json", out)
    with open(RESULTS / "rag_results.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["variant", "recall5", "mrr", "ndcg10", "recall5_ge4_reqs", "p95_latency_s"])
        for v, d in out["variants"].items():
            o = d["overall"]; w.writerow([v, o["recall5"], o["mrr"], o["ndcg10"], o["recall5_ge4_reqs"], o["p95_latency_s"]])


if __name__ == "__main__":
    main()
