"""R&D question A: does tool granularity change agent behaviour?  40 tasks with known correct calls x 4 tool-set designs:
  fine (24 single-purpose tools), coarse (3 'do-everything' tools with an action arg),
  best_terse (the 11+3 real MCP tools with minimal descriptions), best (the real tools with rewritten descriptions).
Metrics: tool-selection accuracy, argument accuracy (given right tool), tokens per task.  -> evals/results/tool_design.json"""
from __future__ import annotations

import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor

import httpx

from agent.config import load_config
from evals.common import write

S = lambda **k: k  # noqa: E731
# (nl task, intent, args)
TASKS = [
    ("Find jobs that need Celery experience.", "search_skill", S(skill="Celery")),
    ("Show me open jobs requiring dbt.", "search_skill", S(skill="dbt")),
    ("Any jobs asking for Playwright?", "search_skill", S(skill="Playwright")),
    ("List jobs in the Web Development category.", "search_cat", S(category="Web Development")),
    ("What's open in Data Analysis right now?", "search_cat", S(category="Data Analysis")),
    ("Browse AI & Machine Learning jobs.", "search_cat", S(category="AI & Machine Learning")),
    ("Search jobs mentioning 'churn'.", "search_text", S(q="churn")),
    ("Look for postings that mention dashboard.", "search_text", S(q="dashboard")),
    ("Get the full post for job job-ml-0010.", "get_job", S(job_id="job-ml-0010")),
    ("Open job job-web-0042 and show me everything.", "get_job", S(job_id="job-web-0042")),
    ("What is the budget of job job-data-0007?", "job_budget", S(job_id="job-data-0007")),
    ("How many Connects does job job-ml-0100 cost?", "job_connects", S(job_id="job-ml-0100")),
    ("Which skills does job job-web-0003 require?", "job_skills", S(job_id="job-web-0003")),
    ("What is the title of job job-data-0050?", "job_title", S(job_id="job-data-0050")),
    ("Show history for client client-017.", "client", S(client_id="client-017")),
    ("How much has client-003 spent in total?", "client_spend", S(client_id="client-003")),
    ("What is client-044's hire rate?", "client_hire", S(client_id="client-044")),
    ("Is client-009's payment verified?", "client_pay", S(client_id="client-009")),
    ("How many Connects do I have left?", "connects", S()),
    ("What's my Connects balance?", "connects", S()),
    ("Show the thread for proposal prop-00003.", "messages", S(proposal_id="prop-00003")),
    ("Read the client messages on proposal prop-00011.", "messages", S(proposal_id="prop-00011")),
    ("List all my submitted proposals and their statuses.", "proposals", S()),
    ("What's the median budget for Web Development jobs?", "price_median", S(category="Web Development")),
    ("Give me market price stats for Data Analysis.", "price_stats", S(category="Data Analysis")),
    ("What is the 25th percentile budget in AI & Machine Learning?", "price_p25", S(category="AI & Machine Learning")),
    ("Find evidence in my portfolio for Kubernetes.", "evidence", S(requirement="Kubernetes")),
    ("Do I have experience with Stripe payments? Search my portfolio.", "evidence", S(requirement="Stripe payments")),
    ("Search my past work for LoRA fine-tuning.", "evidence", S(requirement="LoRA fine-tuning")),
    ("Find portfolio items about A/B testing.", "evidence", S(requirement="A/B testing")),
    ("Open case study ml-proj-03.", "case", S(id="ml-proj-03")),
    ("Show me the case study web-proj-12 in full.", "case", S(id="web-proj-12")),
    ("Which skills does my portfolio cover?", "skills", S()),
    ("What interview slots am I free for in the next 3 days?", "slots", S(days=3)),
    ("Find my free slots this week.", "slots", S(days=5)),
    ("When am I free over the next 2 days?", "slots", S(days=2)),
    ("What are the current platform rules and limits?", "policy", S()),
    ("Does the platform currently multiply Connects costs?", "policy", S()),
    ("Show every conversation thread I have.", "threads", S()),
    ("List all my message threads across proposals.", "threads", S()),
]


def T(name, desc, props=None, req=None):
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props or {}, "required": req if req is not None else list((props or {}).keys())}}}


STR = {"type": "string"}
FINE = {  # intent -> (tool, argmap)
    "search_skill": "search_jobs_by_skill", "search_cat": "search_jobs_by_category", "search_text": "search_jobs_by_text",
    "get_job": "get_job_description", "job_budget": "get_job_budget", "job_connects": "get_job_connects_cost",
    "job_skills": "get_job_skills", "job_title": "get_job_title", "client": "get_client_rating", "client_spend": "get_client_spend",
    "client_hire": "get_client_hire_rate", "client_pay": "get_client_payment_verified", "connects": "get_connects_balance",
    "messages": "list_messages_for_proposal", "proposals": "list_proposals", "price_median": "get_price_median",
    "price_stats": "get_price_p75", "price_p25": "get_price_p25", "evidence": "search_evidence_by_requirement",
    "case": "get_case_study", "skills": "list_skills", "slots": "get_free_slots", "policy": "get_platform_policy", "threads": "list_all_threads"}
FINE_TOOLS = [
    T("search_jobs_by_skill", "Search jobs by a skill.", {"skill": STR}), T("search_jobs_by_category", "Search jobs by category.", {"category": STR}),
    T("search_jobs_by_text", "Search jobs by free text.", {"q": STR}), T("get_job_title", "Get a job's title.", {"job_id": STR}),
    T("get_job_description", "Get a job's full description/post.", {"job_id": STR}), T("get_job_budget", "Get a job's budget.", {"job_id": STR}),
    T("get_job_skills", "Get a job's required skills.", {"job_id": STR}), T("get_job_connects_cost", "Get a job's Connects cost.", {"job_id": STR}),
    T("get_client_spend", "Get a client's total spend.", {"client_id": STR}), T("get_client_hire_rate", "Get a client's hire rate.", {"client_id": STR}),
    T("get_client_rating", "Get a client's average rating / history summary.", {"client_id": STR}),
    T("get_client_payment_verified", "Is the client's payment verified?", {"client_id": STR}), T("get_connects_balance", "Get my Connects balance."),
    T("list_messages_for_proposal", "List messages in one proposal thread.", {"proposal_id": STR}), T("list_all_threads", "List all message threads."),
    T("list_proposals", "List my proposals."), T("get_price_median", "Median job budget in a category.", {"category": STR}),
    T("get_price_p25", "25th percentile budget in a category.", {"category": STR}), T("get_price_p75", "75th percentile budget in a category.", {"category": STR}),
    T("search_evidence_by_requirement", "Search portfolio evidence for a requirement.", {"requirement": STR}),
    T("get_case_study", "Get a portfolio case study by id.", {"id": STR}), T("list_skills", "List portfolio skills."),
    T("get_free_slots", "Get free calendar slots.", {"days": {"type": "integer"}}), T("get_platform_policy", "Get platform policy."),
]
COARSE_TOOLS = [
    T("marketplace", "Query the marketplace. action: search_jobs|get_job|client|connects|messages|proposals|price_stats|policy. params: object.",
      {"action": STR, "params": {"type": "object"}}),
    T("portfolio", "Query my portfolio. action: search_evidence|get_case_study|list_skills. params: object.", {"action": STR, "params": {"type": "object"}}),
    T("workspace", "Calendar/email. action: free_slots|hold|email_draft. params: object.", {"action": STR, "params": {"type": "object"}}),
]
COARSE_MAP = {"search_skill": ("marketplace", "search_jobs"), "search_cat": ("marketplace", "search_jobs"), "search_text": ("marketplace", "search_jobs"),
              "get_job": ("marketplace", "get_job"), "job_budget": ("marketplace", "get_job"), "job_connects": ("marketplace", "get_job"),
              "job_skills": ("marketplace", "get_job"), "job_title": ("marketplace", "get_job"), "client": ("marketplace", "client"),
              "client_spend": ("marketplace", "client"), "client_hire": ("marketplace", "client"), "client_pay": ("marketplace", "client"),
              "connects": ("marketplace", "connects"), "messages": ("marketplace", "messages"), "threads": ("marketplace", "messages"),
              "proposals": ("marketplace", "proposals"), "price_median": ("marketplace", "price_stats"), "price_stats": ("marketplace", "price_stats"),
              "price_p25": ("marketplace", "price_stats"), "policy": ("marketplace", "policy"), "evidence": ("portfolio", "search_evidence"),
              "case": ("portfolio", "get_case_study"), "skills": ("portfolio", "list_skills"), "slots": ("workspace", "free_slots")}
BEST = {"search_skill": "search_jobs", "search_cat": "search_jobs", "search_text": "search_jobs", "get_job": "get_job", "job_budget": "get_job",
        "job_connects": "get_job", "job_skills": "get_job", "job_title": "get_job", "client": "get_client_history", "client_spend": "get_client_history",
        "client_hire": "get_client_history", "client_pay": "get_client_history", "connects": "get_connects_balance", "messages": "list_messages",
        "threads": "list_messages", "proposals": "list_proposals", "price_median": "get_price_stats", "price_stats": "get_price_stats",
        "price_p25": "get_price_stats", "policy": "get_platform_policy", "evidence": "search_evidence", "case": "get_case_study",
        "skills": "list_skills", "slots": "free_slots"}


def real_tools(terse: bool) -> list[dict]:
    from mcp_servers.marketplace.server import create_server as m
    from mcp_servers.portfolio.server import create_server as p
    from mcp_servers.workspace.server import create_server as w
    out = []
    for srv in (m(), p(), w()):
        for t in asyncio.run(srv.list_tools()):
            if t.name in ("create_proposal_draft", "submit_proposal", "send_message", "create_interview_hold", "create_email_draft"):
                continue
            schema = {k: v for k, v in t.inputSchema.items() if k != "title"}
            props = {k: {kk: vv for kk, vv in v.items() if kk != "title"} for k, v in schema.get("properties", {}).items()}
            props.pop("user_id", None)
            props.pop("persona", None)
            schema["properties"] = props
            schema["required"] = [r for r in schema.get("required", []) if r in props]
            desc = t.name.replace("_", " ") if terse else (t.description or "")
            out.append({"type": "function", "function": {"name": t.name, "description": desc, "parameters": schema}})
    return out


def norm(v):
    return str(v).strip().lower()


def args_ok(got: dict, exp: dict, intent: str, design: str) -> bool:
    if design == "coarse":
        got = {**got.get("params", {})} if isinstance(got.get("params"), dict) else {}
    for k, v in exp.items():
        gv = got.get(k)
        if gv is None and k == "q":
            gv = got.get("query") or got.get("text")
        if norm(gv) != norm(v):
            return False
    return True


def run_one(design, tools, task, key, base, model):
    nl, intent, exp = task
    body = {"model": model, "temperature": 0, "tools": tools, "tool_choice": "auto", "max_tokens": 200, **({"reasoning_effort": "none"} if "11434" in base else {}),
            "messages": [{"role": "system", "content": "You are GigBid's tool-using agent. Call exactly one tool that answers the user's request."},
                         {"role": "user", "content": nl}]}
    r = httpx.post(f"{base}/chat/completions", json=body, headers={"Authorization": f"Bearer {key}"}, timeout=90)
    d = r.json()
    u = d.get("usage", {})
    calls = d["choices"][0]["message"].get("tool_calls") or []
    tool, args = (calls[0]["function"]["name"], json.loads(calls[0]["function"]["arguments"] or "{}")) if calls else (None, {})
    if design == "fine":
        exp_tool = FINE[intent]
    elif design == "coarse":
        exp_tool, act = COARSE_MAP[intent]
        ok_sel = tool == exp_tool and norm(args.get("action", "")).replace("-", "_") in (act, act.replace("_jobs", ""), act + "s", "search" if act == "search_jobs" else act)
    else:
        exp_tool = BEST[intent]
    if design != "coarse":
        ok_sel = tool == exp_tool
    ok_args = ok_sel and args_ok(args, exp, intent, design)
    return {"intent": intent, "sel": ok_sel, "args": ok_args, "tokens": u.get("prompt_tokens", 0) + u.get("completion_tokens", 0), "called": tool}


def main():
    cfg = load_config()["models"]
    local = os.environ.get("MODEL_PROFILE", "").startswith("local")  # local Ollama model: separate result file, DeepSeek file stays intact
    if local:
        key, base = "ollama", os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        model = cfg["profiles"][os.environ["MODEL_PROFILE"]]["default"]["model"]
    else:
        key = os.environ["DEEPSEEK_API_KEY"]
        base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model = cfg["profiles"]["open"]["default"]["model"]
    sets = {"fine": FINE_TOOLS, "coarse": COARSE_TOOLS, "best_terse": real_tools(True), "best_rewritten": real_tools(False)}
    out = {"model": model, "n_tasks": len(TASKS), "designs": {}}
    for name, tools in sets.items():
        d = "fine" if name == "fine" else "coarse" if name == "coarse" else "best"
        with ThreadPoolExecutor(1 if local else 8) as ex:
            res = list(ex.map(lambda t: run_one(d, tools, t, key, base, model), TASKS))
        out["designs"][name] = {"n_tools": len(tools), "tool_selection_acc": round(sum(r["sel"] for r in res) / len(res), 3),
                                "argument_acc": round(sum(r["args"] for r in res) / len(res), 3),
                                "tokens_per_task": round(sum(r["tokens"] for r in res) / len(res), 1),
                                "failures": [{"task": t[0], "called": r["called"]} for t, r in zip(TASKS, res) if not r["args"]][:12]}
        print(name, {k: v for k, v in out["designs"][name].items() if k != "failures"}, flush=True)
    write("tool_design_local_qwen.json" if local else "tool_design.json", out)


if __name__ == "__main__":
    main()
