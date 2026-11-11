"""Long-term memory on a LangGraph Store (SqliteStore locally; swap for PostgresStore via DATABASE_URL).
Namespaces: (user, 'style') and (user, 'outcome'). Writes go ONLY through promotion_rules.py."""
from __future__ import annotations

import os
import sqlite3
from functools import lru_cache

from langgraph.store.sqlite import SqliteStore

from agent.config import ROOT


@lru_cache
def get_store() -> SqliteStore:
    path = os.environ.get("GIGBID_STATE_DIR", str(ROOT / "data/processed"))
    os.makedirs(path, exist_ok=True)
    conn = sqlite3.connect(os.path.join(path, "memory.sqlite"), check_same_thread=False, isolation_level=None)
    st = SqliteStore(conn)
    st.setup()
    return st


def list_memories(user: str, kind: str) -> list[dict]:
    return [{"key": i.key, **i.value} for i in get_store().search((user, kind), limit=200)]


def delete_memory(user: str, kind: str, key: str) -> None:
    get_store().delete((user, kind), key)
