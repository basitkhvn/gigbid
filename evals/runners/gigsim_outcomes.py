"""GigSim simulated outcomes. (1) reply/hire rate per RETRIEVAL variant on a fixed job set (does better retrieval help replies?)
(2) X2 signature extension: A/B test of two proposal strategies with significance tests.
Letters are template-built from retrieved evidence (LLM-free, so this is cheap and deterministic); the simulated client's
decision rule is in gigsim_local/app.py (_decide). CAVEAT: both letter generator and sim reward naming required skills, so
absolute rates are optimistic; only the *relative* comparison is informative.  -> evals/results/gigsim_outcomes.json, ab_experiment.json"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import uuid

os.environ.setdefault("GIGBID_STATE_DIR", tempfile.mkdtemp(prefix="gb_out_"))
os.environ.setdefault("GIGSIM_RATE_LIMIT", "1000000")
os.environ.setdefault("GIGSIM_CONNECTS", "10000000")
os.environ.setdefault("MODEL_PROFILE", "offline")

from fastapi.testclient import TestClient  # noqa: E402
from scipy import stats  # noqa: E402

from evals.common import PERSONAS, dev, write  # noqa: E402
from gigsim_local.app import app, register_jobs  # noqa: E402
from rag.requirements import extract  # noqa: E402
from rag.retriever import retrieve  # noqa: E402

C = TestClient(app)
PROFILE = {p: json.load(open(f"data/personas/{p}/profile.json")) for p in PERSONAS}


def covered_by(persona, evidence, req):
    proj = {p["project_id"]: p for p in PROFILE[persona]["projects"]}
    for n, e in enumerate(evidence):
        pj = proj.get(e.get("project"))
        if pj and req in pj["skills"] and e["type"] != "proposal":
            return n + 1, pj
    return None, None


def letter_evidence(persona, job, evidence):
    reqs = extract(job)
    lines = []
    for r in reqs:
        n, pj = covered_by(persona, evidence, r)
        if n:
            lines.append(f"For {r}, I applied it in my {pj['title']} project for a {pj['industry']} client and shipped it [E{n}].")
    opener = f"Your {job['industry']} team needs help with {job['title'].split(' for ')[0].lower()}, and I have delivered similar work."
    return " ".join([opener] + lines + ["I would be glad to share a short plan and first milestone with you." + " " * 0]) + " " + "x" * 0


def per_req_evidence(persona, job):
    """What the shipped pipeline does: one retrieval per requirement (non-proposal evidence), merged."""
    from rag.retriever import search_text
    seen, ev = set(), []
    for r in extract(job):
        for e in search_text(persona, r, 3, {"types": ["case_study", "readme", "review", "cv"]}):
            if e["id"] not in seen:
                seen.add(e["id"]); ev.append(e)
    return ev


def letter_generic(persona, job):
    reqs = extract(job)
    return ("I am passionate about this opportunity and a hardworking freelancer. I have skills in " + ", ".join(reqs) +
            ". I can start right away and deliver quality work on time. Please consider my proposal.").replace("  ", " ")


_cnt: dict = {}


def submit(user, job, text, bid=None):
    _cnt[user] = _cnt.get(user, 0) + 1
    user = f"{user}-{_cnt[user] // 40}"  # stay under the platform daily proposal limit per account
    r = C.post("/proposals", json={"job_id": job["job_id"], "cover_letter": text.ljust(210, " "), "bid": bid or job["budget"]["max"] * 0.95 + 1,
                                   "idempotency_key": uuid.uuid4().hex}, headers={"authorization": user})
    assert r.status_code == 200, r.text
    return r.json()["status"]


def rates(statuses):
    n = len(statuses)
    return {"n": n, "reply_rate": round(sum(s in ("replied", "interview", "hired") for s in statuses) / n, 3),
            "hire_rate": round(sum(s == "hired" for s in statuses) / n, 3)}


def main(n):
    out = {"by_variant": {}}
    jobs = {p: [j for j in dev(p) if j["gold"]["kind"] == "good" and j["gold"]["bid"]][:n] for p in PERSONAS}
    for p in PERSONAS:
        register_jobs(jobs[p])
    for v in ["v0", "v1", "v2", "v3", "v4", "v5", "v8", "v_best", "shipped_per_requirement", "generic_baseline"]:
        st, per = [], {}
        for p in PERSONAS:
            s = []
            for j in jobs[p]:
                job = {k: x for k, x in j.items() if k != "gold"}
                if v == "generic_baseline":
                    text = letter_generic(p, job)
                elif v == "shipped_per_requirement":
                    text = letter_evidence(p, job, per_req_evidence(p, job))
                else:
                    ev = retrieve(p, job, k=5, variant=v)
                    text = letter_evidence(p, job, ev)
                s.append(submit(f"{v}-{p}", job, text))
            per[p] = rates(s); st += s
        out["by_variant"][v] = {"overall": rates(st), "by_persona": per}
        print(v, out["by_variant"][v]["overall"], flush=True)
    write("gigsim_outcomes.json", out)

    # ---- X2: A/B experiment on the same jobs (paired): A = evidence-grounded tailored (v_best), B = generic skills-list
    A, B, A2 = [], [], []
    for p in PERSONAS:
        for j in jobs[p]:
            job = {k: x for k, x in j.items() if k != "gold"}
            A.append(submit(f"A-{p}", job, letter_evidence(p, job, retrieve(p, job, k=5, variant="v_best"))) in ("replied", "interview", "hired"))
            A2.append(submit(f"A2-{p}", job, letter_evidence(p, job, per_req_evidence(p, job))) in ("replied", "interview", "hired"))
            B.append(submit(f"B-{p}", job, letter_generic(p, job)) in ("replied", "interview", "hired"))
    a2 = sum(A2)
    A, a, b = A2, a2, sum(B)  # primary comparison: shipped strategy (per-requirement grounded evidence) vs generic
    n_ = len(A)
    z_tab = [[a, n_ - a], [b, n_ - b]]
    fisher = stats.fisher_exact(z_tab)
    both, only_a, only_b = sum(x and y for x, y in zip(A, B)), sum(x and not y for x, y in zip(A, B)), sum(y and not x for x, y in zip(A, B))
    mc = stats.binomtest(only_a, only_a + only_b, 0.5).pvalue if only_a + only_b else 1.0
    write("ab_experiment.json", {"strategy_A": "evidence-grounded, per-requirement retrieval (as shipped), cited projects", "strategy_B": "generic skills list",
                                 "n_jobs": n_,  "reply_A": round(a / n_, 3), "reply_B": round(b / n_, 3), "fisher_exact_p": float(fisher[1]),
                                 "mcnemar_exact_p_paired": float(mc), "only_A": only_a, "only_B": only_b, "both": both,
                                 "caveat": "simulated clients reward skill mentions and penalise generic phrasing by construction (see DATA_CARD)"})
    print("A/B", a / n_, b / n_, fisher[1], mc)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=60); main(ap.parse_args().n)
