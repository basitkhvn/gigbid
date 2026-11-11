"""Full bid-graph evaluation (to the approval gate, then approve -> GigSim for the simulated outcome).
Measures per job: decision, unsupported claims before/after verification, critic loops, compliance, latency, tokens, USD,
and the GigSim simulated status (replied/interview/hired/ignored).
Usage: python -m evals.runners.proposal_eval --profile open --n 8 --tag open_flash
-> evals/results/proposals_<tag>.json"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
import time

os.environ.setdefault("GIGBID_STATE_DIR", tempfile.mkdtemp(prefix="gb_prop_"))
os.environ.setdefault("MARKETPLACE_RATE_PER_MIN", "100000")
os.environ.setdefault("GIGSIM_RATE_LIMIT", "100000")
os.environ.setdefault("GIGSIM_CONNECTS", "1000000")

from langgraph.types import Command  # noqa: E402

from agent.checkpointer import make_checkpointer  # noqa: E402
from agent.graphs.bid_graph import build_bid_graph  # noqa: E402
from agent.tracing import new_trace_id, summarize  # noqa: E402
from evals.common import PERSONAS, dev, mean, pct, write  # noqa: E402
from gigsim_local.app import register_jobs  # noqa: E402

PROFILE = {"ml": {"rate": 55, "floor": 35}, "web": {"rate": 48, "floor": 30}, "data": {"rate": 40, "floor": 25}}


async def one(g, persona, j, sem, user):
    async with sem:
        tid = new_trace_id()
        cfg = {"configurable": {"thread_id": f"eval:{user}:{j['job_id']}:{tid}"}}
        t0 = time.time()
        inp = {"user_id": user, "persona": persona, "profile": PROFILE[persona], "job_id": j["job_id"], "trace_id": tid}
        out = await g.ainvoke(inp, cfg)
        res = {"job": j["job_id"], "persona": persona, "gold_bid": j["gold"]["bid"], "kind": j["gold"]["kind"],
               "pred": (out.get("decision") or {}).get("action", out.get("status")), "status": out.get("status")}
        if out.get("draft"):
            cs = out.get("claim_stats") or {}
            res.update({"unsupported_before": cs.get("unsupported_before"), "claims_before": cs.get("claims_before"),
                        "unsupported_after": cs.get("unsupported_after"), "claims_after": cs.get("claims_after"),
                        "critic_loops": out.get("revisions", 0), "compliance_violations": len((out.get("compliance") or {}).get("violations", [])),
                        "text": out["draft"]["cover_letter"], "evidence_ids": out["draft"].get("evidence_ids")})
            st = await g.aget_state(cfg)
            if st.next:
                out2 = await g.ainvoke(Command(resume={"action": "approve"}), cfg)
                res["sim_status"] = (out2.get("submission") or {}).get("status")
        s = summarize(tid)
        res.update({"latency_s": round(time.time() - t0, 2), "tokens": s["tokens_in"] + s["tokens_out"], "usd": s["usd"]})
        return res


async def main(a):
    from mcp_servers.marketplace.server import create_server  # noqa: F401
    results = []
    async with make_checkpointer() as cp:
        g = build_bid_graph(cp)
        sem = asyncio.Semaphore(a.conc)
        tasks = []
        for p in a.personas:
            jobs = [j for j in dev(p) if j["gold"]["kind"] in ("good", "injection", "weak", "scam")]
            # balanced fixed subset: the first n of each kind mix, deterministic
            sub = [j for j in jobs if j["gold"]["kind"] == "good"][: a.n] + [j for j in jobs if j["gold"]["kind"] == "scam"][: a.scam]
            register_jobs(sub)
            tasks += [one(g, p, j, sem, f"eval-{p}-{a.tag}") for j in sub]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    ok = [r for r in results if isinstance(r, dict)]
    errs = [repr(r) for r in results if not isinstance(r, dict)]
    drafted = [r for r in ok if "text" in r]
    sent = [r for r in drafted if r.get("sim_status")]
    summ = {"tag": a.tag, "profile": os.environ.get("MODEL_PROFILE"), "n_jobs": len(ok), "n_drafted": len(drafted), "errors": errs[:5],
            "unsupported_per_proposal_before": mean(r["unsupported_before"] for r in drafted),
            "unsupported_per_proposal_after": mean(r["unsupported_after"] for r in drafted),
            "claims_per_proposal": mean(r["claims_before"] for r in drafted),
            "critic_loops_mean": mean(r["critic_loops"] for r in drafted),
            "reply_rate": round(sum(r["sim_status"] in ("replied", "interview", "hired") for r in sent) / len(sent), 3) if sent else None,
            "hire_rate": round(sum(r["sim_status"] == "hired" for r in sent) / len(sent), 3) if sent else None, "n_sent": len(sent),
            "p50_latency_s": pct([r["latency_s"] for r in ok], .5), "p95_latency_s": pct([r["latency_s"] for r in ok], .95),
            "tokens_per_job": mean(r["tokens"] for r in ok), "usd_per_job": mean(r["usd"] for r in ok),
            "usd_per_proposal": mean(r["usd"] for r in drafted)}
    write(f"proposals_{a.tag}.json", {"summary": summ, "jobs": ok})
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="open"); ap.add_argument("--n", type=int, default=8); ap.add_argument("--scam", type=int, default=2)
    ap.add_argument("--tag", default="open_flash"); ap.add_argument("--conc", type=int, default=6)
    ap.add_argument("--personas", nargs="+", default=PERSONAS)
    a = ap.parse_args()
    os.environ["MODEL_PROFILE"] = a.profile
    asyncio.run(main(a))
