from __future__ import annotations

import numpy as np

from rag.corpus import Corpus


def rrf(rankings: list[list[int]], k: int = 60) -> dict[int, float]:
    s: dict[int, float] = {}
    for r in rankings:
        for pos, i in enumerate(r):
            s[i] = s.get(i, 0.0) + 1.0 / (k + pos + 1)
    return s


def to_evidence(corpus: Corpus, scored: list[tuple[dict, float]], k: int, how: str = "") -> list[dict]:
    """Collapse chunks to items (best chunk wins), return top-k evidence items."""
    best: dict[str, tuple[dict, float]] = {}
    for c, s in scored:
        if c["id"] not in best or s > best[c["id"]][1]:
            best[c["id"]] = (c, s)
    out = []
    for c, s in sorted(best.values(), key=lambda x: -x[1])[:k]:
        out.append({"id": c["id"], "type": c["type"], "project": c.get("project"), "title": c.get("title"),
                    "source": c["id"], "date": c.get("date"), "outcome": c.get("outcome"), "industry": c.get("industry"),
                    "skills": c.get("skills", []), "score": round(float(s), 5), "text": corpus.by_id[c["id"]]["text"],
                    "via": how})
    return out


def job_query(job: dict) -> str:
    return job.get("title", "") + ". " + job.get("description", "")


def minmax(xs):
    xs = np.asarray(xs, dtype=float)
    return (xs - xs.min()) / (xs.max() - xs.min() + 1e-9) if len(xs) else xs
