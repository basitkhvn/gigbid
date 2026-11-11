"""Factory: variant chosen by config (agent/config.yaml rag.variant) or argument."""
from __future__ import annotations

from agent.config import load_config
from rag.corpus import get_corpus
from rag.variants import vs

VARIANTS = {"v0": vs.v0_naive, "v1": vs.v1_decompose, "v2": vs.v2_hybrid, "v3": vs.v3_rerank, "v4": vs.v4_outcome,
            "v5": vs.v5_multivector, "v6": vs.v6_contextual, "v7": vs.v7_hyde, "v8": vs.v8_corrective, "v_best": vs.v_best}


def retrieve(persona: str, job: dict, k: int | None = None, variant: str | None = None, **opts) -> list[dict]:
    cfg = load_config()["rag"]
    v = variant or cfg["variant"]
    return VARIANTS[v](get_corpus(persona), job, k or cfg["k"], **opts)


def search_text(persona: str, text: str, k: int = 5, filters: dict | None = None) -> list[dict]:
    """Free-text requirement search used by the Portfolio MCP server (v_best on a pseudo-job)."""
    ev = retrieve(persona, {"title": text, "description": f"experience with {text}"}, k=max(k * 3, 10) if filters else k)
    for key, val in (filters or {}).items():
        ev = [e for e in ev if e.get(key) == val]
    return ev[:k]
