from __future__ import annotations

from agent.config import load_config
from agent.handoffs import PriceQuote
from agent.mcp_client import ToolUnavailable, get_hub
from agent.nodes.common import node


@node("pricing")
async def pricing(state):
    hub, uid, job = get_hub(), state["user_id"], state["job"]
    prof, spec = state.get("profile", {}), state["job_spec"]
    stats = await hub.call("pricing", "get_price_stats", {"user_id": uid, "category": job.get("category", "")})
    bal = (await hub.call("pricing", "get_connects_balance", {"user_id": uid})).get("balance")
    try:  # connects cost reflects the CURRENT platform policy; fall back to the cached job if it is gone
        job_fresh = await hub.call("scout", "get_job", {"user_id": uid, "job_id": job["job_id"]})
    except ToolUnavailable:
        raise
    except Exception:  # noqa: BLE001
        job_fresh = job
    cost = int(job_fresh.get("connects_cost", job.get("connects_cost", 8)))
    rules = load_config()["platform_rules"]
    rate, floor = prof.get("rate", 45), prof.get("floor", 30)
    hours = 6 * max(1, len(spec["required_skills"]))
    lo, hi = floor * hours * 1.1, rate * hours * 1.2
    budget = spec.get("budget_max") or 0
    bid = min(max(budget * 0.95 if budget else stats.get("median", lo), lo), hi)
    weekly = prof.get("weekly_connects_budget", rules["weekly_connects_budget_default"])
    spent = prof.get("connects_spent_this_week", 0)
    fit = state.get("fit_report", {}).get("score", 0)
    worth = (bal is None or bal >= cost) and spent + cost <= weekly and fit >= 0.5 and (budget == 0 or budget >= lo * 0.7)
    why = (f"Estimated {hours}h at ${floor}-{rate}/h => ${lo:.0f}-${hi:.0f}; client budget ${budget:.0f}; market median "
           f"${stats.get('median', 'n/a')}. Connects cost {cost} (balance {bal}, weekly budget left {weekly - spent}).")
    q = PriceQuote(bid=round(bid, 2), low=round(lo, 2), high=round(hi, 2), connects_cost=cost, worth_connects=bool(worth), rationale=why)
    return {"price_quote": q.model_dump()}
