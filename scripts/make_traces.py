"""Produces the four trace exhibits in docs/traces/ (PII-masked JSONL + a small summary each):
 scam_skipped, approved_proposal, critic_loop, crash_and_resume.  Uses the `open` profile (needs DEEPSEEK_API_KEY)."""
import asyncio
import json
import os
import shutil
import tempfile

os.environ.setdefault("GIGBID_STATE_DIR", tempfile.mkdtemp(prefix="gb_trace_"))
os.environ.setdefault("MODEL_PROFILE", "open")
os.environ.update({"MARKETPLACE_RATE_PER_MIN": "100000", "GIGSIM_RATE_LIMIT": "100000", "GIGSIM_CONNECTS": "1000000"})
from langgraph.types import Command  # noqa: E402

from agent.checkpointer import make_checkpointer  # noqa: E402
from agent.config import ROOT  # noqa: E402
from agent.graphs.bid_graph import build_bid_graph  # noqa: E402
from agent.tracing import TRACE_DIR, new_trace_id, summarize  # noqa: E402
from evals.common import dev  # noqa: E402
from gigsim_local.app import register_jobs  # noqa: E402

PROF = {"rate": 55, "floor": 35}
OUT = ROOT / "docs/traces"


def keep(name, tid, extra):
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(TRACE_DIR / f"{tid}.jsonl", OUT / f"{name}.jsonl")
    s = {"exhibit": name, **summarize(tid), **extra}
    (OUT / f"{name}.summary.json").write_text(json.dumps(s, indent=1))
    print(name, s)


async def main():
    jobs = dev("ml")
    register_jobs(jobs)
    good = [j for j in jobs if j["gold"]["kind"] == "good" and j["gold"]["bid"]]
    scam = next(j for j in jobs if j["gold"]["scam"])
    async with make_checkpointer() as cp:
        g = build_bid_graph(cp)

        async def run(j, uid, thread):
            tid = new_trace_id()
            cfg = {"configurable": {"thread_id": thread}}
            out = await g.ainvoke({"user_id": uid, "persona": "ml", "profile": PROF, "job_id": j["job_id"], "trace_id": tid}, cfg)
            return tid, cfg, out

        tid, cfg, out = await run(scam, "tr-scam", "tr-scam-1")
        keep("scam_skipped", tid, {"job": scam["job_id"], "decision": out["decision"], "risk_flags": out["risk_report"]["flags"]})

        tid, cfg, out = await run(good[0], "tr-ok", "tr-ok-1")
        out2 = await g.ainvoke(Command(resume={"action": "approve"}), cfg)
        keep("approved_proposal", tid, {"job": good[0]["job_id"], "status": out2["status"], "submission": {k: out2["submission"][k] for k in ("proposal_id", "connects_spent", "status")},
                                         "claim_stats": out["claim_stats"]})

        for j in good[1:12]:
            tid, cfg, out = await run(j, f"tr-loop-{j['job_id']}", f"tr-loop-{j['job_id']}")
            if out.get("revisions", 0) >= 1:
                keep("critic_loop", tid, {"job": j["job_id"], "revisions": out["revisions"], "critiques": out["critiques"]})
                break
        else:
            print("no critic loop observed in 11 jobs (try a different sample)")

    # crash and resume: graph + checkpointer torn down, new ones created, approval still pending, approve -> submitted once
    j = good[12]
    tid = new_trace_id()
    cfg = {"configurable": {"thread_id": "tr-crash-1"}}
    async with make_checkpointer() as cp:
        await build_bid_graph(cp).ainvoke({"user_id": "tr-crash", "persona": "ml", "profile": PROF, "job_id": j["job_id"], "trace_id": tid}, cfg)
    async with make_checkpointer() as cp2:  # "restart"
        g2 = build_bid_graph(cp2)
        pending = (await g2.aget_state(cfg)).next
        out = await g2.ainvoke(Command(resume={"action": "approve"}), cfg)
    keep("crash_and_resume", tid, {"job": j["job_id"], "pending_after_restart": list(pending), "status": out["status"], "submission": out["submission"].get("proposal_id")})


asyncio.run(main())
