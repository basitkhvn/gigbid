"""Portfolio MCP server (A1, read-only). Install: `uvx gigbid-portfolio-mcp` or `docker run gigbid/portfolio-mcp`;
works in Claude Desktop / Cursor (see README in this folder). Persona selected with PORTFOLIO_PERSONA or per call."""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mcp_servers.portfolio import prompts, resources, tools

RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
DEFAULT = os.environ.get("PORTFOLIO_PERSONA", "ml")


def create_server() -> FastMCP:
    mcp = FastMCP("gigbid-portfolio")

    @mcp.tool(annotations=RO)
    def search_evidence(requirement: str, k: int = 5, filters: dict | None = None, persona: str = "") -> list[dict]:
        """Find portfolio evidence for a requirement. Returns items with type, source, date, outcome (for past proposals).
        filters may include type (case_study|readme|review|proposal|cv), project, industry, outcome."""
        return tools.search_evidence(persona or DEFAULT, requirement, max(1, min(k, 20)), filters)

    @mcp.tool(annotations=RO)
    def get_case_study(id: str, persona: str = "") -> dict:
        """Get one full portfolio item by id (e.g. 'ml-proj-03-case' or just 'ml-proj-03')."""
        return tools.get_case_study(persona or DEFAULT, id)

    @mcp.tool(annotations=RO)
    def list_skills(persona: str = "") -> dict:
        """List the skills evidenced in this portfolio with item counts."""
        return tools.list_skills(persona or DEFAULT)

    @mcp.resource("portfolio://case/{id}")
    def case(id: str) -> str:
        """Full case study / README / review by id."""
        return resources.case_resource(DEFAULT, id)

    @mcp.resource("portfolio://proposal/{id}")
    def proposal(id: str) -> str:
        """A past proposal with its outcome (won/replied/ignored)."""
        return resources.proposal_resource(DEFAULT, id)

    for name, tmpl in prompts.PROMPTS.items():
        def make(t=tmpl):
            def fn(question: str = "", job: str = "", skill: str = "") -> str:
                return t.format(question=question, job=job, skill=skill)
            return fn
        mcp.prompt(name=name, description=tmpl.split(":")[0][:100])(make())
    return mcp


if __name__ == "__main__":
    create_server().run()
