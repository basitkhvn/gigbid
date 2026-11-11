"""R7: explicit promotion rules. Nothing enters long-term memory except through these functions.

STYLE (from user edits to drafts): diff original vs edited; derive candidate rules
  (drop_word:<w>, cut_first_sentence, shorter, drop_phrase:<p>); a candidate is PROMOTED to a style rule only when it has
  been observed in >= STYLE_MIN_OBS edits on DISTINCT jobs. Until then it lives as a 'candidate' counter.
OUTCOME (from marketplace outcomes): per (category) accumulate won/replied/ignored; PROMOTED to an outcome insight
  when n >= OUTCOME_MIN_N and the rate differs from the user's baseline by >= OUTCOME_MIN_LIFT. Raw tool output is never stored.
"""
from __future__ import annotations

import difflib
import re

from agent.memory.store import get_store

STYLE_MIN_OBS = 2
OUTCOME_MIN_N = 3
OUTCOME_MIN_LIFT = 0.10


def derive_style_candidates(original: str, edited: str) -> list[tuple[str, str]]:
    cands: list[tuple[str, str]] = []
    o_sents = re.split(r"(?<=[.!?])\s+", original.strip())
    e_sents = re.split(r"(?<=[.!?])\s+", edited.strip())
    if o_sents and (o_sents[0] not in e_sents) and len(e_sents) < len(o_sents):
        cands.append(("cut_first_sentence", "Always cut the first sentence (generic opening)."))
    ow, ew = re.findall(r"[A-Za-z']+", original.lower()), re.findall(r"[A-Za-z']+", edited.lower())
    sm = difflib.SequenceMatcher(a=ow, b=ew)
    for tag, i1, i2, _, _ in sm.get_opcodes():
        if tag == "delete" and 0 < i2 - i1 <= 3:
            w = " ".join(ow[i1:i2])
            if len(w) > 4 and w not in {"the", "and", "with", "that", "this"}:
                cands.append((f"drop_phrase:{w}", f'Avoid the phrase "{w}".'))
    if len(edited) < 0.85 * len(original):
        cands.append(("shorter", "Keep proposals shorter and tighter."))
    return cands


def record_edit(user: str, job_id: str, original: str, edited: str) -> list[dict]:
    """Returns the rules newly promoted by this edit."""
    st, promoted = get_store(), []
    for key, text in derive_style_candidates(original, edited):
        cur = st.get((user, "style_candidates"), key)
        jobs = set(cur.value["jobs"]) if cur else set()
        jobs.add(job_id)
        st.put((user, "style_candidates"), key, {"jobs": sorted(jobs), "text": text})
        if len(jobs) >= STYLE_MIN_OBS and not st.get((user, "style"), key):
            val = {"rule": text, "evidence_jobs": sorted(jobs), "promoted_by": f"seen on {len(jobs)} distinct jobs (>= {STYLE_MIN_OBS})"}
            st.put((user, "style"), key, val)
            promoted.append({"key": key, **val})
    return promoted


def style_rules(user: str) -> list[str]:
    return [i.value["rule"] for i in get_store().search((user, "style"), limit=50)]


def record_outcome(user: str, category: str, status: str, opener: str = "") -> dict | None:
    """status in won|replied|ignored. Promotes an insight for the category when the promotion rule is met."""
    st = get_store()
    cur = st.get((user, "outcome_counts"), category)
    c = cur.value if cur else {"won": 0, "replied": 0, "ignored": 0}
    c[status] = c.get(status, 0) + 1
    st.put((user, "outcome_counts"), category, c)
    allc = [i.value for i in st.search((user, "outcome_counts"), limit=200)]
    tot = sum(sum(v.values()) for v in allc) or 1
    base = sum(v["won"] + v["replied"] for v in allc) / tot
    n = sum(c.values())
    rate = (c["won"] + c["replied"]) / n
    if n >= OUTCOME_MIN_N and abs(rate - base) >= OUTCOME_MIN_LIFT:
        val = {"category": category, "n": n, "reply_or_win_rate": round(rate, 3), "baseline": round(base, 3),
               "insight": f"{category}: {'above' if rate > base else 'below'} your baseline reply rate ({rate:.0%} vs {base:.0%}, n={n})",
               "promoted_by": f"n>={OUTCOME_MIN_N} and |lift|>={OUTCOME_MIN_LIFT}"}
        st.put((user, "outcome"), category, val)
        return val
    return None
