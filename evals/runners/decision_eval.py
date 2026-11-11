"""B4 decisions: bid-or-skip F1, scam precision/recall, price-in-fair-band, injection detection, per persona.
Rule-based (LLM-free) triage path, i.e. what the scheduled scout runs. -> evals/results/decision_eval.json
Usage: python -m evals.runners.decision_eval [--n 200] [--min-fit 0.6]"""
from __future__ import annotations

import argparse
import asyncio
import os
import tempfile

os.environ.setdefault("GIGBID_STATE_DIR", tempfile.mkdtemp(prefix="gb_eval_"))
os.environ.setdefault("MODEL_PROFILE", "offline")
os.environ.setdefault("MARKETPLACE_RATE_PER_MIN", "100000")  # eval harness only; production limiter stays on
os.environ.setdefault("GIGSIM_RATE_LIMIT", "100000")

from agent.config import load_config  # noqa: E402
from evals.common import PERSONAS, dev, write  # noqa: E402
from gigsim_local.app import register_jobs  # noqa: E402


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0}


async def run(n: int):
    from apps.api.triage import triage_job
    out = {"per_persona": {}, "failures": []}
    tot = dict(tp=0, fp=0, fn=0, stp=0, sfp=0, sfn=0, inb=0, inn=0, injd=0, injn=0)
    for p in PERSONAS:
        jobs = dev(p)[:n]
        register_jobs(jobs)
        user = {"id": f"eval-{p}", "persona": p}
        c = dict(tp=0, fp=0, fn=0, stp=0, sfp=0, sfn=0, inb=0, inn=0, injd=0, injn=0)
        for j in jobs:
            t = await triage_job(user, {k: v for k, v in j.items() if k != "gold"}, force=True)
            g = j["gold"]
            pb, gb = t["action"] == "bid", g["bid"]
            c["tp"] += pb and gb; c["fp"] += pb and not gb; c["fn"] += (not pb) and gb
            ps = t["risk"] >= load_config()["thresholds"]["maximum_risk_score"]
            c["stp"] += ps and g["scam"]; c["sfp"] += ps and not g["scam"]; c["sfn"] += (not ps) and g["scam"]
            if pb and gb and t["price"]:
                c["inn"] += 1; c["inb"] += g["fair_band"][0] <= t["price"]["bid"] <= g["fair_band"][1]
            if g["injection"]:
                c["injn"] += 1; c["injd"] += "injection" in t["flags"]
            if pb != gb and len(out["failures"]) < 60:
                out["failures"].append({"job": j["job_id"], "persona": p, "kind": "wrong_bid" if pb else "wrong_skip", "gold_kind": g["kind"],
                                        "fit": t["fit"], "coverage": g["coverage"], "flags": t["flags"]})
            if ps != g["scam"] and len(out["failures"]) < 60:
                out["failures"].append({"job": j["job_id"], "persona": p, "kind": "scam_miss" if g["scam"] else "scam_false_alarm", "flags": t["flags"]})
        out["per_persona"][p] = {"n": len(jobs), "bid_or_skip": prf(c["tp"], c["fp"], c["fn"]), "scam": prf(c["stp"], c["sfp"], c["sfn"]),
                                 "price_in_band": round(c["inb"] / c["inn"], 3) if c["inn"] else None, "n_priced": c["inn"],
                                 "injection_detected": round(c["injd"] / c["injn"], 3) if c["injn"] else None}
        for k in tot:
            tot[k] += c[k]
    out["overall"] = {"bid_or_skip": prf(tot["tp"], tot["fp"], tot["fn"]), "scam": prf(tot["stp"], tot["sfp"], tot["sfn"]),
                      "price_in_band": round(tot["inb"] / tot["inn"], 3) if tot["inn"] else None,
                      "injection_detected": round(tot["injd"] / tot["injn"], 3) if tot["injn"] else None}
    out["config"] = {"thresholds": load_config()["thresholds"], "note": "fit_support_relevance chosen by inspecting score separation on persona skill lists (dev-adjacent)"}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=200); a = ap.parse_args()
    res = asyncio.run(run(a.n))
    write("decision_eval.json", res)
    print(res["overall"]); [print(p, d) for p, d in res["per_persona"].items()]
