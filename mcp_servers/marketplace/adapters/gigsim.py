from __future__ import annotations

import asyncio
from typing import Any

import httpx

from mcp_servers.marketplace.adapters.base import MarketplaceUnavailable


class GigSimAdapter:
    name = "gigsim"

    def __init__(self, base_url: str = "inprocess"):
        if base_url == "inprocess":
            from gigsim_local.app import app
            self.http = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://gigsim", timeout=30)
        else:
            self.http = httpx.AsyncClient(base_url=base_url, timeout=30)

    async def _req(self, method: str, path: str, user: str, **kw) -> Any:
        """Bounded retries with backoff on 429/5xx/connection errors (C7)."""
        err: Exception | None = None
        for attempt in range(4):
            try:
                r = await self.http.request(method, path, headers={"authorization": user}, **kw)
                if r.status_code == 429 or r.status_code >= 500:
                    await asyncio.sleep(min(0.4 * 2 ** attempt, 3) if r.status_code != 429 else float(r.headers.get("retry-after", 1)) / 5)
                    err = RuntimeError(f"{r.status_code}")
                    continue
                if r.status_code >= 400:
                    raise ValueError(f"GigSim {r.status_code}: {r.json().get('detail', r.text)}")
                return r.json()
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                err = e
                await asyncio.sleep(0.4 * 2 ** attempt)
        raise MarketplaceUnavailable(f"marketplace unavailable: {err}")

    async def search_jobs(self, user, q, category, skill, limit, offset):
        return await self._req("GET", "/jobs", user, params={"q": q, "category": category, "skill": skill, "limit": limit, "offset": offset})

    async def get_job(self, user, job_id): return await self._req("GET", f"/jobs/{job_id}", user)
    async def get_client(self, user, client_id): return await self._req("GET", f"/clients/{client_id}", user)
    async def get_connects(self, user): return await self._req("GET", "/connects", user)
    async def get_price_stats(self, user, category): return await self._req("GET", "/stats/price", user, params={"category": category})
    async def get_policy(self, user): return await self._req("GET", "/policy", user)
    async def list_messages(self, user, proposal_id): return await self._req("GET", f"/messages/{proposal_id}", user)
    async def list_threads(self, user): return await self._req("GET", "/messages", user)
    async def list_proposals(self, user): return await self._req("GET", "/proposals", user)
    async def submit_proposal(self, user, payload): return await self._req("POST", "/proposals", user, json=payload)
    async def send_message(self, user, payload): return await self._req("POST", "/messages", user, json=payload)
