"""Cheap, LLM-free triage used by the inbox and the scheduled scout: risk + fit + decision + price for one job."""
from __future__ import annotations

import json

from agent.llm import no_llm
from agent.nodes.fit_matcher import fit_matcher
from agent.nodes.pricing import pricing
from agent.nodes.risk_assessor import risk_assessor
from agent.nodes.analyst import analyst
from agent.graphs.bid_graph import decide
from agent.tracing import new_trace_id
from apps.api.db import db, get_settings, now, one


def _init():
    db().execute("CREATE TABLE IF NOT EXISTS triage(user_id TEXT, job_id TEXT, data TEXT, ts REAL, PRIMARY KEY(user_id,job_id))")


async def triage_job(user: dict, job: dict, force: bool = False) -> dict:
    _init()
    if not force:
        r = one("SELECT data FROM triage WHERE user_id=? AND job_id=?", user["id"], job["job_id"])
        if r:
            return json.loads(r["data"])
    st = {"user_id": user["id"], "persona": user["persona"], "job": job, "job_id": job["job_id"],
          "profile": get_settings(user["id"]), "trace_id": new_trace_id()}
    with no_llm():
        for fn in (analyst, risk_assessor, fit_matcher):
            st.update(await fn(st))
        st.update(await decide(st))
        out = {"job_id": job["job_id"], "action": st["decision"]["action"], "reasons": st["decision"]["reasons"],
               "fit": st["fit_report"]["score"], "risk": st["risk_report"]["score"], "flags": st["risk_report"]["flags"],
               "matches": st["fit_report"]["matches"], "job_spec": st["job_spec"], "risk_report": st["risk_report"],
               "fit_report": st["fit_report"], "price": None}
        if st["decision"]["action"] == "bid":
            st.update(await pricing(st))
            out["price"] = st["price_quote"]
    db().execute("INSERT OR REPLACE INTO triage VALUES (?,?,?,?)", (user["id"], job["job_id"], json.dumps(out), now()))
    return out
