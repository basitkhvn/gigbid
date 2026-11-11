import json
from collections import Counter, defaultdict

from fastapi import APIRouter, Depends

from agent.mcp_client import ToolUnavailable, get_hub
from agent.memory import promotion_rules as mem
from agent.tracing import summarize
from apps.api.auth.users import current_user
from apps.api.db import rows

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
async def analytics(user: dict = Depends(current_user)):
    try:
        props = (await get_hub().call("ui", "list_proposals", {"user_id": user["id"]}))["proposals"]
    except ToolUnavailable:
        props = []
    cat = {r["job_id"]: r["category"] for r in rows("SELECT job_id,category FROM runs WHERE user_id=? AND kind='bid'", user["id"])}
    by_cat: dict = defaultdict(lambda: {"sent": 0, "replied": 0, "hired": 0, "connects": 0})
    for p in props:
        c = by_cat[cat.get(p["job_id"], "other")]
        c["sent"] += 1
        c["connects"] += p["connects_spent"]
        c["replied"] += p["status"] in ("replied", "interview", "hired")
        c["hired"] += p["status"] == "hired"
        # feed outcomes to long-term memory ONLY through the promotion rule
        mem.record_outcome(user["id"], cat.get(p["job_id"], "other"), "won" if p["status"] == "hired" else "replied" if p["status"] in ("replied", "interview") else "ignored")
    runs_ = rows("SELECT * FROM runs WHERE user_id=? AND kind='bid'", user["id"])
    cost, lat = [], []
    for r in runs_:
        if r["trace_id"]:
            s = summarize(r["trace_id"]); cost.append(s["usd"]); lat.append(s["latency_s"])
    lat.sort()
    reasons = Counter()
    for e in rows("SELECT r.status, e.node, e.data FROM run_events e JOIN runs r ON r.id=e.run_id WHERE r.user_id=? AND e.node IN ('rejected','decide','compliance')", user["id"]):
        d = json.loads(e["data"])
        if e["node"] == "decide" and "skip" in d.get("summary", ""):
            reasons["skipped: " + d["summary"][:60]] += 1
        elif e["node"] == "compliance" and "passed=False" in d.get("summary", ""):
            reasons["blocked by compliance"] += 1
    for e in rows("SELECT e.data FROM run_events e JOIN runs r ON r.id=e.run_id WHERE r.user_id=? AND e.node='__resume__'", user["id"]):
        pass
    return {"by_category": by_cat, "totals": {"sent": len(props), "connects_spent": sum(p["connects_spent"] for p in props),
            "runs": len(runs_), "avg_usd_per_run": round(sum(cost) / len(cost), 5) if cost else 0,
            "p95_latency_s": lat[int(0.95 * (len(lat) - 1))] if lat else 0}, "top_reasons": reasons.most_common(6)}
