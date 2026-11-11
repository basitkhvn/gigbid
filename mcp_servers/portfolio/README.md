# gigbid-portfolio MCP server

Read-only MCP server over a freelancer's portfolio (case studies, READMEs, reviews, past proposals with outcomes).

Tools: `search_evidence(requirement,k,filters)`, `get_case_study(id)`, `list_skills()`.
Resources: `portfolio://case/{id}`, `portfolio://proposal/{id}`. Prompts: `answer_screening_question`, `draft_cover_letter`, `what_have_i_won_with`.

Claude Desktop / Cursor config:
```json
{"mcpServers":{"gigbid-portfolio":{"command":"uv","args":["run","--directory","/path/to/gigbid","python","-m","mcp_servers.portfolio.server"],"env":{"PORTFOLIO_PERSONA":"ml"}}}}
```
Docker: `docker build -f infra/docker/mcp.Dockerfile -t gigbid-portfolio . && docker run -i -e PORTFOLIO_PERSONA=ml gigbid-portfolio`.
Publishing to PyPI as `gigbid-portfolio-mcp` is a TODO (see docs/TOOLS.md).
