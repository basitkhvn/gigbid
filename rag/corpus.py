"""Per-persona corpus with all index flavours the variants need (built lazily, cached)."""
from __future__ import annotations

from functools import lru_cache

from rag.index.stores import Index
from rag.ingest.loaders import chunk, load_items

OUTCOME_W = {"won": 1.0, "replied": 0.5, "ignored": 0.0}


class Corpus:
    def __init__(self, persona: str):
        self.persona = persona
        self.items = load_items(persona)
        self.by_id = {i["id"]: i for i in self.items}
        self.chunks = [c for it in self.items for c in chunk(it)]
        self._plain = None
        self._ctx = None
        self._multi = None
        self.project_title = {i["project"]: i["title"] for i in self.items if i["type"] == "case_study"}
        self.project_outcome = self._outcomes()

    def _outcomes(self) -> dict[str, float]:
        agg: dict[str, list[float]] = {}
        for it in self.items:
            if it["type"] == "proposal" and it.get("outcome"):
                agg.setdefault(it["project"], []).append(OUTCOME_W[it["outcome"]])
        # shrink towards the global mean (small samples)
        allv = [v for vs in agg.values() for v in vs] or [0.0]
        mu = sum(allv) / len(allv)
        return {p: (sum(vs) + 3 * mu) / (len(vs) + 3) for p, vs in agg.items()}

    @property
    def plain(self) -> Index:
        if self._plain is None:
            self._plain = Index(self.chunks)
        return self._plain

    @property
    def contextual(self) -> Index:  # V6: context line prepended to each chunk
        if self._ctx is None:
            cc = []
            for c in self.chunks:
                ctx = f"[{c['type']} | project: {self.project_title.get(c.get('project'), c.get('title'))} | industry: {c.get('industry')}] "
                cc.append({**c, "ctx_text": ctx + c["chunk_text"]})
            self._ctx = Index(cc, text_key="ctx_text")
        return self._ctx

    @property
    def multivector(self) -> Index:  # V5: one doc per (project, facet); returned as a project
        if self._multi is None:
            docs = []
            for it in self.items:
                if it.get("project") and it["type"] in ("case_study", "readme", "review"):
                    docs.append({**it, "chunk_id": it["id"], "chunk_text": it["text"], "facet": it["type"]})
            self._multi = Index(docs)
        return self._multi


@lru_cache(maxsize=8)
def get_corpus(persona: str) -> Corpus:
    return Corpus(persona)


def invalidate(persona: str) -> None:
    get_corpus.cache_clear()
