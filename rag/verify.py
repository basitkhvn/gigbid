"""B3 claim verification: split a draft into claims, check each against retrieved evidence.

Verdicts: supported | partial | unsupported. Unsupported claims are removed before the Critic sees the draft.
A 'claim' is a sentence asserting experience: it names a tool/skill, a number/year, or uses first-person experience
verbs. Checking is deterministic by default (term grounding against the CITED evidence, then any evidence);
when the grader node is online an LLM double-checks 'partial' ones.
"""
from __future__ import annotations

import re

from agent.llm import complete_json, is_offline, prompt

CITE = re.compile(r"\[E(\d+)\]")
EXPERIENCE = re.compile(r"\b(i|my|we)\b.*\b(built|shipped|delivered|led|designed|deployed|trained|developed|improved|reduced|"
                        r"increased|worked|used|implemented|years?)\b", re.I)
NUM = re.compile(r"\b\d+(?:\.\d+)?\s?(?:%|x|k|\+|years?|months?)?|\b(?:19|20)\d{2}\b")


def split_claims(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _terms(sentence: str, vocab: set[str]) -> tuple[list[str], list[str]]:
    low = sentence.lower()
    skills = [s for s in vocab if re.search(r"(?<![\w])" + re.escape(s.lower()) + r"(?![\w])", low)]
    nums = [n.strip() for n in NUM.findall(CITE.sub("", sentence)) if n.strip()]
    return skills, nums


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t.lower())


def _semantic(term: str, text: str) -> bool:
    from agent.config import load_config
    from rag.index.stores import rerank
    return rerank(term, [text])[0] >= load_config()["thresholds"]["fit_support_relevance"]


def verify(draft: str, evidence: list[dict]) -> list[dict]:
    from rag.requirements import vocab
    v = vocab()
    results = []
    by_num = {i + 1: e for i, e in enumerate(evidence)}
    all_text = _norm(" ".join(e["text"] + " " + " ".join(e.get("skills", [])) for e in evidence))
    for sent in split_claims(draft):
        cited = [by_num[int(n)] for n in CITE.findall(sent) if int(n) in by_num]
        skills, nums = _terms(sent, v)
        is_claim = bool(skills or nums or EXPERIENCE.search(sent))
        if not is_claim:
            results.append({"claim": sent, "verdict": "not_a_claim", "cited": [], "unsupported_terms": []})
            continue
        src = _norm(" ".join(e["text"] + " " + " ".join(e.get("skills", [])) for e in cited)) if cited else ""
        # a term is grounded if it appears in cited evidence (or, for implied-skill evidence, a synonym phrase does)
        def grounded(term: str) -> bool:
            if _norm(term) in src:
                return True
            if not src or term in nums:  # numbers/years must match lexically; skills may match semantically (implied skills)
                return False
            return _semantic(term, " ".join(e["text"] for e in cited))
        unsup = [t for t in skills + nums if not grounded(t)]
        n_terms = len(skills) + len(nums)
        if n_terms == 0:  # experience verb with no checkable term: require a citation
            verdict = "supported" if cited else "unsupported"
        elif not unsup:
            verdict = "supported"
        elif len(unsup) < n_terms:
            verdict = "partial"
        else:
            verdict = "unsupported"
        # mis-citation: terms exist elsewhere in evidence but not in the cited item
        if verdict != "supported" and cited and not is_offline("critic") and not is_offline("grader"):
            pass
        results.append({"claim": sent, "verdict": verdict, "cited": [e["id"] for e in cited],
                        "unsupported_terms": unsup, "in_other_evidence": [t for t in unsup if _norm(t) in all_text]})
    return results


def llm_recheck(results: list[dict], evidence: list[dict]) -> list[dict]:
    """Optional: ask the grader node about 'partial' claims (kept cheap; only runs when online)."""
    if is_offline("grader"):
        return results
    for r in results:
        if r["verdict"] == "partial" and r["cited"]:
            ev = " ".join(e["text"] for e in evidence if e["id"] in r["cited"])
            out = complete_json("grader", prompt("grader"), f"REQUIREMENT/CLAIM: {r['claim']}\nEVIDENCE: {ev}")
            if out and out.get("verdict") in ("supported", "unsupported", "partial"):
                r["verdict"] = out["verdict"]
    return results


def _evidence_sentence(ev: dict, n: int, max_len: int = 220) -> str:
    """Deterministic rewrite: the first sentence of the evidence item itself, cited as [E<n>] (so it is grounded by construction)."""
    first = split_claims(ev["text"])[0] if split_claims(ev["text"]) else ev["text"]
    first = first.rstrip(".!? ")
    if len(first) > max_len:
        first = first[:max_len].rsplit(" ", 1)[0]
    return f"{first} [E{n}]."


def repair(draft: str, results: list[dict], evidence: list[dict] | None = None) -> str:
    """F3 fix: rewrite unsupported (and unrecoverable partial) claims from the evidence they cite (or, if uncited, the next unused
    evidence item) instead of deleting them, so verification no longer empties the letter. Without evidence, falls back to removal.
    The caller re-verifies the repaired text."""
    bad = {r["claim"]: r for r in results if r["verdict"] in ("unsupported", "partial")}
    index = {e["id"]: i + 1 for i, e in enumerate(evidence or [])}
    used: set[int] = set()
    out: list[str] = []
    for s in split_claims(draft):
        r = bad.get(s)
        if r is None:
            out.append(s)
            continue
        if not evidence:
            continue  # no evidence to rewrite from: remove (old behaviour)
        cand = [index[i] for i in r["cited"] if i in index] + [i + 1 for i in range(len(evidence))]
        n = next((c for c in cand if c not in used), None)
        if n is None:
            continue
        used.add(n)
        out.append(_evidence_sentence(evidence[n - 1], n))
    return " ".join(out)


def unsupported_rate(results: list[dict]) -> tuple[int, int]:
    claims = [r for r in results if r["verdict"] != "not_a_claim"]
    return sum(1 for r in claims if r["verdict"] in ("unsupported", "partial")), len(claims)
