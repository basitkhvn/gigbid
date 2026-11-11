"""Ablate the shipped pipeline (v_best) one component at a time. -> evals/results/ablation.json"""
from __future__ import annotations

import argparse

from evals.common import PERSONAS, write
from evals.runners.rag_eval import evaluate, jobs_for, summarize

CONFIGS = {"shipped (decompose+hybrid+outcome)": {}, "+rerank_for_ranking": {"rerank_rank": True}, "-decomposition": {"decompose": False},
           "-hybrid(BM25)": {"hybrid": False}, "-outcome_boost": {"outcome": False}}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=60); a = ap.parse_args()
    out = {}
    for name, opts in CONFIGS.items():
        rows_all, per = [], {}
        for p in PERSONAS:
            rows = evaluate("v_best", p, jobs_for(p, a.n), **opts)
            per[p] = summarize(rows); rows_all += rows
        out[name] = {"overall": summarize(rows_all), "by_persona": per}
        print(name, out[name]["overall"], flush=True)
    write("ablation.json", out)


if __name__ == "__main__":
    main()
