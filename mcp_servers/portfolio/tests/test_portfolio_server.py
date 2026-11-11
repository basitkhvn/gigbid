import json

from mcp.shared.memory import create_connected_server_and_client_session as conn

from mcp_servers.portfolio.server import create_server


async def test_tools_resources_prompts():
    async with conn(create_server()._mcp_server) as s:
        assert {t.name for t in (await s.list_tools()).tools} == {"search_evidence", "get_case_study", "list_skills"}
        r = await s.call_tool("search_evidence", {"requirement": "Celery", "k": 3, "persona": "web"})
        items = json.loads(r.content[0].text) if r.content[0].text.startswith("[") else r.structuredContent["result"]
        assert items and {"type", "source", "date", "outcome"} <= set(items[0])
        res = await s.read_resource("portfolio://case/ml-proj-01-case")
        assert "ml-proj-01" in str(res) or res.contents
        assert (await s.list_prompts()).prompts
