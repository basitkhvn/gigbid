"""GigSim-local: a small marketplace simulator (REST). Stand-in for the official GigSim.

Features: jobs with search, clients with histories, per-user Connects, proposals, messages,
per-token rate limiting (429), optional injected 5xx errors, simulated clients with HIDDEN
preferences deciding reply / interview / hire, and a policy file that can change at runtime.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

SEED = Path(os.environ.get("GIGSIM_SEED_DIR", Path(__file__).resolve().parent.parent / "data/gigsim_seed"))
RATE_LIMIT_PER_MIN = int(os.environ.get("GIGSIM_RATE_LIMIT", "60"))
ERROR_RATE = float(os.environ.get("GIGSIM_ERROR_RATE", "0.0"))
STARTING_CONNECTS = int(os.environ.get("GIGSIM_CONNECTS", "200"))

app = FastAPI(title="GigSim-local", version="0.1")
JOBS: dict[str, dict] = {}
CLIENTS: dict[str, dict] = {}
USERS: dict[str, dict] = {}  # token/user -> state
_hits: dict[str, list[float]] = {}


def _load() -> None:
    JOBS.clear()
    CLIENTS.clear()
    if (SEED / "jobs.jsonl").exists():
        for line in (SEED / "jobs.jsonl").read_text().splitlines():
            j = json.loads(line)
            JOBS[j["job_id"]] = j
    if (SEED / "clients.json").exists():
        for c in json.loads((SEED / "clients.json").read_text()):
            CLIENTS[c["client_id"]] = c


_load()


def register_jobs(jobs: list[dict]) -> None:
    """Test/eval helper: add jobs (e.g. the dev set, minus gold labels) to the simulator's catalogue."""
    for j in jobs:
        JOBS[j["job_id"]] = {k: v for k, v in j.items() if k != "gold"}
        if j.get("client_id") and j["client_id"] not in CLIENTS:
            CLIENTS[j["client_id"]] = {"client_id": j["client_id"], "name": j["client_id"], "country": "US", "total_spent": 1000,
                                        "hire_rate": 0.4, "avg_rating": 4.5, "payment_verified": True, "reviews_given": 5,
                                        "_hidden": {"dislikes_generic": True, "budget_ceiling_factor": 1.1}}


def policy() -> dict:
    p = SEED / "policy.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _user(token: str) -> dict:
    return USERS.setdefault(token, {"connects": STARTING_CONNECTS, "proposals": {}, "messages": {}, "idem": {}, "sent_today": 0})


@app.middleware("http")
async def guard(request: Request, call_next):
    if request.url.path.startswith("/health") or request.url.path.startswith("/admin"):
        return await call_next(request)
    tok = request.headers.get("authorization", "anon")
    now = time.time()
    hits = [t for t in _hits.get(tok, []) if now - t < 60]
    if len(hits) >= RATE_LIMIT_PER_MIN:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "rate limited"}, status_code=429, headers={"Retry-After": "5"})
    hits.append(now)
    _hits[tok] = hits
    if ERROR_RATE and random.random() < ERROR_RATE:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "simulated upstream error"}, status_code=503)
    return await call_next(request)


@app.get("/health")
def health():
    return {"ok": True, "jobs": len(JOBS)}


@app.get("/policy")
def get_policy():
    return policy()


def _public_client(c: dict) -> dict:
    return {k: v for k, v in c.items() if not k.startswith("_")}


@app.get("/jobs")
def search_jobs(q: str = "", category: str = "", skill: str = "", limit: int = 25, offset: int = 0):
    out = []
    for j in JOBS.values():
        if category and j.get("category") != category:
            continue
        if skill and skill.lower() not in [s.lower() for s in j["required_skills"]]:
            continue
        if q and q.lower() not in (j["title"] + " " + j["description"]).lower():
            continue
        out.append(j)
    return {"total": len(out), "jobs": out[offset: offset + limit]}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "job not found")
    j = dict(JOBS[job_id])
    j["connects_cost"] = int(round(j.get("connects_cost", 8) * policy().get("connects_multiplier", 1.0)))
    return j


@app.get("/clients/{client_id}")
def get_client(client_id: str):
    if client_id not in CLIENTS:
        raise HTTPException(404, "client not found")
    return _public_client(CLIENTS[client_id])


@app.get("/stats/price")
def price_stats(category: str = ""):
    xs = sorted(j["budget"]["max"] for j in JOBS.values() if j["budget"]["max"] > 0 and (not category or j.get("category") == category))
    if not xs:
        return {"n": 0}
    q = lambda p: xs[int(p * (len(xs) - 1))]
    return {"n": len(xs), "p25": q(0.25), "median": q(0.5), "p75": q(0.75)}


@app.get("/connects")
def connects(authorization: str = Header("anon")):
    return {"balance": _user(authorization)["connects"]}


class ProposalIn(BaseModel):
    job_id: str
    cover_letter: str
    bid: float
    screening_answers: list[str] = []
    idempotency_key: str


def _decide(job: dict, client: dict, prop: dict) -> str:
    """Hidden-preference client model (rule-based stand-in for the LLM client)."""
    text = prop["cover_letter"].lower()
    skills = [s.lower() for s in job["required_skills"]]
    mention = sum(1 for s in skills if s in text) / max(1, len(skills))
    score = 0.25 * mention * 4  # up to 1.0
    generic = any(p in text for p in ("passionate", "dear sir", "hardworking", "i am writing to apply"))
    if generic and client["_hidden"]["dislikes_generic"]:
        score -= 0.5
    if prop["bid"] > job["budget"]["max"] * client["_hidden"]["budget_ceiling_factor"] and job["budget"]["max"] > 0:
        score -= 0.4
    if len(text) < 200:
        score -= 0.3
    if str(job.get("client_id")) and "similar" in text or "shipped" in text:
        score += 0.2
    h = int(hashlib.sha256((job["job_id"] + prop["cover_letter"]).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    if score >= 0.9 and h < 0.5:
        return "hired"
    if score >= 0.6 and h < 0.7:
        return "interview"
    if score >= 0.4 and h < 0.7:
        return "replied"
    if score >= 0.2 and h < 0.25:
        return "viewed"
    return "ignored"


@app.post("/proposals")
def create_proposal(p: ProposalIn, authorization: str = Header("anon")):
    u = _user(authorization)
    if p.idempotency_key in u["idem"]:
        return u["idem"][p.idempotency_key]
    if p.job_id not in JOBS:
        raise HTTPException(404, "job not found")
    pol = policy()
    job = JOBS[p.job_id]
    if len(p.cover_letter) < pol.get("min_cover_letter_chars", 0):
        raise HTTPException(422, f"cover letter shorter than {pol['min_cover_letter_chars']} chars")
    if len(p.cover_letter) > pol.get("max_cover_letter_chars", 10**6):
        raise HTTPException(422, "cover letter too long")
    cost = int(round(job.get("connects_cost", 8) * pol.get("connects_multiplier", 1.0)))
    if u["connects"] < cost:
        raise HTTPException(402, "insufficient connects")
    if u["sent_today"] >= pol.get("daily_proposal_limit", 50):
        raise HTTPException(429, "daily proposal limit reached")
    u["connects"] -= cost
    u["sent_today"] += 1
    client = CLIENTS[job["client_id"]]
    status = _decide(job, client, p.model_dump())
    rec = {"proposal_id": f"prop-{len(u['proposals']) + 1:05d}", "job_id": p.job_id, "status": status,
           "connects_spent": cost, "bid": p.bid, "cover_letter": p.cover_letter}
    u["proposals"][rec["proposal_id"]] = rec
    if status in ("replied", "interview", "hired"):
        msg = {"replied": "Thanks for applying! Could you share more about a similar project?",
               "interview": "Your proposal looks great. Can we schedule an interview this week?",
               "hired": "We'd like to hire you. What is your start date?"}[status]
        u["messages"].setdefault(rec["proposal_id"], []).append({"from": "client", "text": msg, "ts": time.time()})
    u["idem"][p.idempotency_key] = rec
    return rec


@app.get("/proposals")
def list_proposals(authorization: str = Header("anon")):
    return list(_user(authorization)["proposals"].values())


class MessageIn(BaseModel):
    proposal_id: str
    text: str
    idempotency_key: str


@app.get("/messages/{proposal_id}")
def list_messages(proposal_id: str, authorization: str = Header("anon")):
    return _user(authorization)["messages"].get(proposal_id, [])


@app.get("/messages")
def all_threads(authorization: str = Header("anon")):
    return {k: v for k, v in _user(authorization)["messages"].items()}


@app.post("/messages")
def send_message(m: MessageIn, authorization: str = Header("anon")):
    u = _user(authorization)
    if m.idempotency_key in u["idem"]:
        return u["idem"][m.idempotency_key]
    if m.proposal_id not in u["proposals"]:
        raise HTTPException(404, "proposal not found")
    rec = {"from": "freelancer", "text": m.text, "ts": time.time()}
    u["messages"].setdefault(m.proposal_id, []).append(rec)
    u["idem"][m.idempotency_key] = rec
    return rec


@app.post("/admin/reset")
def reset():
    USERS.clear()
    _hits.clear()
    _load()
    return {"ok": True}
