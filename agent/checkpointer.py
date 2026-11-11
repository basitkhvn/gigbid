"""C6 durability: Postgres checkpointer when DATABASE_URL is set (docker compose / deployment), SQLite otherwise."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from agent.config import ROOT


@asynccontextmanager
async def make_checkpointer():
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgres"):
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        async with AsyncPostgresSaver.from_conn_string(url.replace("+psycopg", "")) as cp:
            await cp.setup()
            yield cp
    else:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        d = os.environ.get("GIGBID_STATE_DIR", str(ROOT / "data/processed"))
        os.makedirs(d, exist_ok=True)
        async with AsyncSqliteSaver.from_conn_string(os.path.join(d, "checkpoints.sqlite")) as cp:
            yield cp
