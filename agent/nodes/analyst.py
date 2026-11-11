from __future__ import annotations

from agent.guard import sanitize, wrap_untrusted
from agent.handoffs import JobSpec
from agent.llm import complete_json, prompt
from agent.nodes.common import node
from rag.requirements import extract


@node("analyst")
async def analyst(state):
    job = state["job"]
    clean = sanitize(job["description"])
    spec = None
    out = complete_json("analyst", prompt("analyst"), wrap_untrusted(job["title"] + "\n" + clean))
    if out:
        try:
            spec = JobSpec(job_id=job["job_id"], title=job["title"], category=job.get("category", ""),
                           deliverables=[str(x) for x in out.get("deliverables", [])][:8],
                           required_skills=[str(x) for x in out.get("required_skills", [])][:10],
                           budget_min=out.get("budget_min"), budget_max=out.get("budget_max"),
                           timeline_days=out.get("timeline_days"), hidden_needs=[str(x) for x in out.get("hidden_needs", [])][:5],
                           screening_questions=[str(x) for x in out.get("screening_questions", [])][:5])
        except Exception:  # noqa: BLE001
            spec = None
    if spec is None:  # offline / fallback model
        b = job.get("budget", {})
        spec = JobSpec(job_id=job["job_id"], title=job["title"], category=job.get("category", ""),
                       required_skills=extract({"title": job["title"], "description": clean}),
                       budget_min=b.get("min"), budget_max=b.get("max"), screening_questions=job.get("screening_questions", []))
    if not spec.budget_max:
        spec.budget_max = job.get("budget", {}).get("max")
    return {"job_spec": spec.model_dump()}
