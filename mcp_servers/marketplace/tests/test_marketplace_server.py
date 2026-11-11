import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session as conn

from mcp_servers.marketplace.server import RateLimiter, create_server


def text(r):
    return json.loads(r.content[0].text)


async def test_submit_is_idempotent_and_spends_connects_once():
    async with conn(create_server()._mcp_server) as s:
        base = {"user_id": "t-idem", "job_id": "job-ml-0000", "cover_letter": "x" * 60, "bid": 100, "idempotency_key": "draft-key-1", "dry_run": False}
        d = (await s.call_tool("create_proposal_draft", {"inp": base})).structuredContent
        sub = {"inp": {"user_id": "t-idem", "draft_id": d["draft_id"], "idempotency_key": "submit-key-1"}}
        b0 = text(await s.call_tool("get_connects_balance", {"user_id": "t-idem"}))["balance"]
        r1, r2 = await s.call_tool("submit_proposal", sub), await s.call_tool("submit_proposal", sub)
        b1 = text(await s.call_tool("get_connects_balance", {"user_id": "t-idem"}))["balance"]
        assert text(r1)["proposal_id"] == text(r2)["proposal_id"] and text(r2).get("replayed")
        assert b0 - b1 == text(r1)["connects_spent"]  # charged exactly once


async def test_dry_run_sends_nothing():
    async with conn(create_server()._mcp_server) as s:
        before = text(await s.call_tool("get_connects_balance", {"user_id": "t-dry"}))["balance"]
        out = (await s.call_tool("create_proposal_draft", {"inp": {"user_id": "t-dry", "job_id": "job-ml-0000", "cover_letter": "y" * 60,
                                                                    "bid": 50, "idempotency_key": "dry-key-001", "dry_run": True}})).structuredContent
        assert out["dry_run"] and out["draft_id"] is None and out["connects_cost"] > 0
        assert text(await s.call_tool("get_connects_balance", {"user_id": "t-dry"}))["balance"] == before


async def test_input_validation_rejects_bad_writes():
    async with conn(create_server()._mcp_server) as s:
        r = await s.call_tool("create_proposal_draft", {"inp": {"user_id": "u", "job_id": "j", "cover_letter": "short", "bid": -5, "idempotency_key": "k"}})
        assert r.isError


async def test_audit_log_is_append_only_and_masks_pii():
    srv = create_server()
    async with conn(srv._mcp_server) as s:
        await s.call_tool("create_proposal_draft", {"inp": {"user_id": "t-aud", "job_id": "job-ml-0000", "bid": 10, "dry_run": False,
                          "cover_letter": "Contact me at boss@fastcash.example please " * 2, "idempotency_key": "aud-key-001", "trace_id": "trace123"}})
    db = srv._gigbid_store.db
    rows = db.execute("SELECT args, trace_id FROM audit WHERE user='t-aud'").fetchall()
    assert rows and rows[0][1] == "trace123" and "fastcash" not in rows[0][0]
    with pytest.raises(Exception):
        db.execute("DELETE FROM audit")


def test_rate_limiter():
    rl = RateLimiter(2)
    rl.check("u"); rl.check("u")
    with pytest.raises(RuntimeError):
        rl.check("u")
