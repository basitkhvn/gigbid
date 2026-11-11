"""Index layer: Qdrant (local, embedded) vector store, BM25, cross-encoder reranker, with on-disk
embedding cache so re-indexing is incremental."""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache

import numpy as np
from rank_bm25 import BM25Okapi

from agent.config import ROOT, load_config

CACHE = ROOT / "data/processed/embcache"


@lru_cache
def _embedder():
    from fastembed import TextEmbedding
    return TextEmbedding(load_config()["models"]["embeddings"])


@lru_cache
def _reranker():
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    return TextCrossEncoder(load_config()["models"]["reranker"])


def embed(texts: list[str]) -> np.ndarray:
    """Cached by content hash; only unseen texts are embedded (incremental indexing)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out: list[np.ndarray | None] = []
    todo: list[tuple[int, str]] = []
    for i, t in enumerate(texts):
        h = hashlib.sha1(t.encode()).hexdigest()
        f = CACHE / f"{h}.npy"
        if f.exists():
            out.append(np.load(f))
        else:
            out.append(None)
            todo.append((i, t))
    if todo:
        vecs = list(_embedder().embed([t for _, t in todo]))
        for (i, t), v in zip(todo, vecs):
            v = np.asarray(v, dtype="float32")
            v /= np.linalg.norm(v) + 1e-9
            np.save(CACHE / f"{hashlib.sha1(t.encode()).hexdigest()}.npy", v)
            out[i] = v
    return np.vstack(out)


def tok(s: str) -> list[str]:
    return re.findall(r"[a-z0-9+#.]+", s.lower())


def rerank(query: str, docs: list[str]) -> list[float]:
    return [float(s) for s in _reranker().rerank(query, docs)]


class Index:
    """Chunks + dense vectors (Qdrant local) + BM25 over the same chunks."""

    def __init__(self, chunks: list[dict], text_key: str = "chunk_text"):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams
        self.chunks = chunks
        self.text_key = text_key
        texts = [c[text_key] for c in chunks]
        self.vecs = embed(texts)
        self.bm25 = BM25Okapi([tok(t) for t in texts])
        self.qd = QdrantClient(":memory:")
        self.col = "chunks"
        self.qd.create_collection(self.col, vectors_config=VectorParams(size=self.vecs.shape[1], distance=Distance.COSINE))
        self.qd.upsert(self.col, [PointStruct(id=i, vector=self.vecs[i].tolist(),
                                              payload={k: v for k, v in c.items() if k != text_key and isinstance(v, (str, int, float, list, type(None)))})
                                  for i, c in enumerate(chunks)])

    def dense(self, query: str, k: int = 30, flt: dict | None = None) -> list[tuple[int, float]]:
        q = embed([query])[0]
        from qdrant_client.models import FieldCondition, Filter, MatchValue
        f = Filter(must=[FieldCondition(key=k_, match=MatchValue(value=v)) for k_, v in (flt or {}).items()]) if flt else None
        res = self.qd.query_points(self.col, query=q.tolist(), limit=k, query_filter=f).points
        return [(p.id, p.score) for p in res]

    def sparse(self, query: str, k: int = 30) -> list[tuple[int, float]]:
        s = self.bm25.get_scores(tok(query))
        idx = np.argsort(-s)[:k]
        return [(int(i), float(s[i])) for i in idx if s[i] > 0]
