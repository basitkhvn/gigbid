"""Requirement extraction used by decomposition variants (rule-based + LLM)."""
from __future__ import annotations

import re

from agent.llm import complete_json, is_offline, prompt

SKILL_VOCAB: set[str] = set()


def vocab() -> set[str]:
    if not SKILL_VOCAB:
        from data.generate import SKILLS
        for d in SKILLS.values():
            SKILL_VOCAB.update(d)
    return SKILL_VOCAB


def rule_based(text: str) -> list[str]:
    reqs = [m.strip() for m in re.findall(r"experience with ([^;.]+)", text)]
    if not reqs:
        low = text.lower()
        reqs = [s for s in vocab() if s.lower() in low]
    return list(dict.fromkeys(reqs))


def extract(job: dict, use_llm: bool = False) -> list[str]:
    text = job.get("title", "") + ". " + job.get("description", "")
    if use_llm and not is_offline("analyst"):
        out = complete_json("analyst", prompt("decompose") + ' Return {"requirements":[...]}.', f"<job_post>{text}</job_post>")
        if out and out.get("requirements"):
            return [str(x) for x in out["requirements"]][:8]
    return rule_based(text) or [job.get("title", "")]
