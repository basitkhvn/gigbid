"""LLM access: model per node from config, fallback model, cost + token accounting, tracing."""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import asyncio
import concurrent.futures as cf

import httpx

_POOL = cf.ThreadPoolExecutor(32)
HARD_DEADLINE_S = 75  # total wall-clock cap per LLM call (provider keep-alives defeat per-read timeouts)

from agent.config import load_config
from agent.tracing import record

PROMPT_DIR = Path(__file__).parent / "prompts"


def prompt(name: str, **fmt) -> str:
    txt = (PROMPT_DIR / f"{name}.md").read_text()
    txt = re.sub(r"^---.*?---\n", "", txt, flags=re.S)
    for k, v in fmt.items():
        txt = txt.replace("{" + k + "}", v)
    return txt.strip()


@dataclass
class LLMResult:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0
    usd: float = 0.0
    latency_s: float = 0.0
    model: str = ""
    fallback: bool = False


import contextvars
from contextlib import contextmanager

_no_llm: contextvars.ContextVar[bool] = contextvars.ContextVar("no_llm", default=False)


@contextmanager
def no_llm():
    """Run rule-based paths only (cheap triage for the inbox / scheduled scouting)."""
    tok = _no_llm.set(True)
    try:
        yield
    finally:
        _no_llm.reset(tok)


def node_model(node: str) -> dict:
    cfg = load_config()["models"]
    prof = cfg["profiles"][cfg["profile"]]
    return {**prof["default"], **prof.get("nodes", {}).get(node, {})}


def is_offline(node: str) -> bool:
    return node_model(node)["provider"] == "offline" or _no_llm.get()


def _call(spec: dict, system: str, user: str, json_mode: bool) -> LLMResult:
    cfg = load_config()["models"]
    prov = cfg["providers"][spec["provider"]]
    key = os.environ.get(prov["key_env"], "")
    if not key:
        raise RuntimeError(f"{prov['key_env']} not set")
    base = os.environ.get(prov["base_url_env"], prov["default_base"])
    body = {"model": spec["model"], "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": spec.get("max_tokens", 600), "temperature": spec.get("temperature", 0.0)}
    if os.environ.get("DEEPSEEK_THINKING") == "disabled":  # multi-agent baselines can't replay reasoning_content; set for ALL systems in a comparison
        body["thinking"] = {"type": "disabled"}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    t0 = time.time()
    fut = _POOL.submit(httpx.post, f"{base}/chat/completions", json=body, headers={"Authorization": f"Bearer {key}"},
                       timeout=httpx.Timeout(60, connect=10))
    try:
        r = fut.result(timeout=HARD_DEADLINE_S)
    except cf.TimeoutError:
        raise TimeoutError(f"LLM call exceeded {HARD_DEADLINE_S}s")
    r.raise_for_status()
    d = r.json()
    u = d.get("usage", {})
    price = cfg["prices"].get(spec["model"], {"in": 0, "out": 0})
    ti, to = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
    return LLMResult(d["choices"][0]["message"]["content"] or "", ti, to, (ti * price["in"] + to * price["out"]) / 1e6,
                     time.time() - t0, spec["model"])


def complete(node: str, system: str, user: str, json_mode: bool = False) -> LLMResult | None:
    """Returns None when the node is configured offline (caller uses its rule-based path).
    On primary failure retries once, then returns None (fallback to rule-based = C7 fallback)."""
    spec = node_model(node)
    if spec["provider"] == "offline" or _no_llm.get():
        return None
    last = None
    for attempt in range(2):
        try:
            res = _call(spec, system, user, json_mode)
            record({"name": node, "kind": "llm", "model": res.model, "tokens_in": res.tokens_in,
                    "tokens_out": res.tokens_out, "usd": res.usd, "latency_s": round(res.latency_s, 3)})
            return res
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    record({"name": node, "kind": "llm", "model": spec["model"], "error": repr(last), "fallback": "offline"})
    return None


def complete_json(node: str, system: str, user: str) -> dict | None:
    res = complete(node, system + "\nRespond with a single JSON object.", user, json_mode=True)
    if res is None:
        return None
    try:
        return json.loads(res.text)
    except Exception:  # noqa: BLE001
        m = re.search(r"\{.*\}", res.text, re.S)
        try:
            return json.loads(m.group(0)) if m else None
        except Exception:  # noqa: BLE001
            return None


async def acomplete(node, system, user, json_mode=False):
    return await asyncio.to_thread(complete, node, system, user, json_mode)


async def acomplete_json(node, system, user):
    return await asyncio.to_thread(complete_json, node, system, user)
