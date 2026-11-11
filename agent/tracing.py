"""Minimal self-hosted tracing: one trace id per run, spans with tokens/cost/latency, PII-masked.

Spans are appended to data/processed/traces/<trace_id>.jsonl and are served by the API
(/runs/{id}/trace). Optional Langfuse export can wrap `record()` (see docs/ARCHITECTURE.md).
"""
from __future__ import annotations

import contextvars
import json
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from agent.config import ROOT
from agent.pii import mask_obj

TRACE_DIR = ROOT / "data/processed/traces"
current_trace: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")


def new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def set_trace(tid: str):
    return current_trace.set(tid)


def record(span: dict) -> None:
    tid = span.get("trace_id") or current_trace.get() or "untraced"
    span = mask_obj({**span, "trace_id": tid, "ts": time.time()})
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    with (TRACE_DIR / f"{tid}.jsonl").open("a") as f:
        f.write(json.dumps(span, default=str) + "\n")


@contextmanager
def span(name: str, kind: str = "node", **attrs):
    t0 = time.time()
    data = {"name": name, "kind": kind, **attrs}
    try:
        yield data
    except Exception as e:  # noqa: BLE001
        data["error"] = repr(e)
        raise
    finally:
        data["latency_s"] = round(time.time() - t0, 3)
        record(data)


def read_trace(tid: str) -> list[dict]:
    p = TRACE_DIR / f"{tid}.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line]


def summarize(tid: str) -> dict:
    spans = read_trace(tid)
    llm = [s for s in spans if s.get("kind") == "llm"]
    return {"trace_id": tid, "spans": len(spans), "tokens_in": sum(s.get("tokens_in", 0) for s in llm),
            "tokens_out": sum(s.get("tokens_out", 0) for s in llm), "usd": round(sum(s.get("usd", 0) for s in llm), 6),
            "latency_s": round(sum(s.get("latency_s", 0) for s in spans if s.get("kind") == "node"), 3)}
