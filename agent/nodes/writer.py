from __future__ import annotations

from agent.guard import sanitize, wrap_untrusted
from agent.handoffs import ProposalDraft
from agent.llm import complete, prompt
from agent.nodes.common import node


def numbered(evidence: list[dict]) -> str:
    return "\n".join(f"[E{i + 1}] ({e['type']}, {e.get('industry')}, {e['title']}) {e['text'][:420]}" for i, e in enumerate(evidence))


def template_letter(state, evidence, instructions: str) -> str:
    """Rule-based fallback writer (offline profile / fallback model): evidence-first, always cited."""
    fit, job = state["fit_report"], state["job"]
    by_id = {e["id"]: (i + 1, e) for i, e in enumerate(evidence)}
    ind = job.get("industry") or "your team"
    sents = [f"Your {ind} project is a close match for the work described below."]
    for m in fit["matches"]:
        if m["supported"] and m["evidence_ids"] and m["evidence_ids"][0] in by_id:
            n, e = by_id[m["evidence_ids"][0]]
            sents.append(f"For {m['requirement']}, I applied it in my {e['title']} project [E{n}].")
    if fit["missing_skills"]:
        sents.append(f"I should be upfront that {', '.join(fit['missing_skills'][:2])} is not a core strength of mine.")
    sents.append("I would be glad to walk you through the approach and a sensible first milestone.")
    return " ".join(sents)


@node("writer")
async def writer(state):
    job, evidence = state["job"], state.get("evidence", [])[:6]
    rules = state.get("style_rules") or []
    crit = (state.get("critiques") or [])[-1:] or []
    instr = crit[0]["revision_instructions"] if crit and not crit[0]["ok"] else ""
    system = prompt("writer", style_rules=("STYLE RULES learned from the user's past edits:\n- " + "\n- ".join(rules)) if rules else "")
    user = (f"{wrap_untrusted(job['title'] + chr(10) + sanitize(job['description']))}\n\nEVIDENCE:\n{numbered(evidence)}\n\n"
            f"Requirements without evidence (do NOT claim): {state['fit_report']['missing_skills']}\n" +
            (f"REVISION INSTRUCTIONS from critic: {instr}\nPrevious draft: {state.get('draft', {}).get('cover_letter', '')}" if instr else ""))
    res = complete("writer", system, user)
    text = res.text.strip() if res else template_letter(state, evidence, instr)
    answers = []
    d = ProposalDraft(job_id=job["job_id"], cover_letter=text, screening_answers=answers,
                      evidence_ids=[e["id"] for e in evidence], revision=state.get("revisions", 0) + (1 if instr else 0))
    return {"draft": d.model_dump(), "evidence": evidence, "revisions": d.revision}
