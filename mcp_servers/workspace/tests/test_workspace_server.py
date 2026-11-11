import json

from mcp.shared.memory import create_connected_server_and_client_session as conn

from mcp_servers.workspace.server import create_server


async def test_hold_and_draft_are_idempotent():
    async with conn(create_server()._mcp_server) as s:
        slots = json.loads((await s.call_tool("free_slots", {"user_id": "w1"})).content[0].text)["slots"]
        a = {"inp": {"user_id": "w1", "start": slots[0], "title": "Interview", "idempotency_key": "hold-key-001"}}
        r1, r2 = await s.call_tool("create_interview_hold", a), await s.call_tool("create_interview_hold", a)
        assert json.loads(r1.content[0].text)["id"] == json.loads(r2.content[0].text)["id"]
        slots2 = json.loads((await s.call_tool("free_slots", {"user_id": "w1"})).content[0].text)["slots"]
        assert slots[0] not in slots2
