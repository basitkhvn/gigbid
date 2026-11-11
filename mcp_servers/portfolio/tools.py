from __future__ import annotations

from rag.corpus import get_corpus
from rag.retriever import search_text


def search_evidence(persona: str, requirement: str, k: int = 5, filters: dict | None = None) -> list[dict]:
    ev = search_text(persona, requirement, k, filters)
    return [{k_: e[k_] for k_ in ("id", "type", "source", "date", "outcome", "project", "title", "industry", "skills", "score", "relevance")}
            | {"snippet": e["text"][:700]} for e in ev]


def get_case_study(persona: str, id_: str) -> dict:
    c = get_corpus(persona)
    it = c.by_id.get(id_) or c.by_id.get(f"{id_}-case")
    if not it:
        raise ValueError(f"no item {id_}")
    return it


def list_skills(persona: str) -> dict:
    c = get_corpus(persona)
    counts: dict[str, int] = {}
    for it in c.items:
        for s in it.get("skills", []):
            counts[s] = counts.get(s, 0) + 1
    return {"skills": sorted(counts, key=lambda s: -counts[s]), "counts": counts}
