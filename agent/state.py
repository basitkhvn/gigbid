"""C2: typed state with reducers. Three things kept apart:
  * STATE (this file): what this job/conversation needs right now (checkpointed in Postgres/SQLite);
  * EXECUTION TRACE: every tool call/LLM call -> agent/tracing.py (JSONL, trace id), plus the lightweight `log` list below;
  * LONG-TERM MEMORY: only promoted knowledge, in a LangGraph Store via agent/memory (explicit promotion rules).
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


def merge_dict(a: dict, b: dict) -> dict:
    return {**(a or {}), **(b or {})}


def last_value(a: str | None, b: str | None) -> str | None:
    """Reducer for `status`: when parallel branches (risk/analyst) both fail in the same step, take the later value instead of crashing."""
    return b if b is not None else a


class BidState(TypedDict, total=False):
    # inputs
    user_id: str
    persona: str
    profile: dict[str, Any]          # rate, floor, filters, autonomy, weekly budget
    trace_id: str
    job_id: str
    # job + parallel analyses (each branch writes its own key; reducers make Send fan-in safe)
    job: dict[str, Any]
    duplicate: bool
    job_spec: dict[str, Any]
    risk_report: dict[str, Any]
    fit_report: dict[str, Any]
    decision: dict[str, Any]
    evidence: list[dict[str, Any]]
    price_quote: dict[str, Any]
    # drafting
    draft: dict[str, Any]
    claim_stats: dict[str, Any]       # unsupported claims before/after verification
    critiques: Annotated[list[dict[str, Any]], operator.add]
    revisions: int
    compliance: dict[str, Any]
    # approval + outcome
    approval: dict[str, Any]
    preview: dict[str, Any]
    submission: dict[str, Any]
    outcome: dict[str, Any]
    # control
    status: Annotated[str, last_value]
    steps: Annotated[int, operator.add]
    log: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]
    degraded: Annotated[dict[str, Any], merge_dict]
    style_rules: list[str]


class ConvState(TypedDict, total=False):
    user_id: str
    persona: str
    proposal_id: str
    trace_id: str
    messages: list[dict[str, Any]]
    intent: str
    reply: dict[str, Any]
    risk_flags: list[str]
    approval: dict[str, Any]
    sent: dict[str, Any]
    status: str
    steps: Annotated[int, operator.add]
    log: Annotated[list[dict[str, Any]], operator.add]
