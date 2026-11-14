"""GigBid API. Typed contract: `make client` generates apps/web/src/lib/api from /openapi.json."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agent.checkpointer import make_checkpointer
from agent.mcp_client import get_hub
from agent.tracing import new_trace_id, set_trace
from apps.api import runs
from apps.api.auth.users import current_user, seed_reviewer
from apps.api.db import db
from apps.api.routers import analytics, approvals, auth, jobs, memory, messages, proposals, run_routes, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    db()
    seed_reviewer()
    async def warm():  # embed/index persona corpora in the background so the first request is fast
        import asyncio

        from rag.corpus import get_corpus
        for p in ("ml", "web", "data"):
            await asyncio.to_thread(lambda p=p: get_corpus(p).plain)

    import asyncio
    # GIGBID_WARM=0 skips the startup pre-indexing (free hosts with 512 MB RAM: indexes are built from the image's baked embedding cache on first use)
    warm_task = asyncio.create_task(warm()) if os.environ.get("GIGBID_WARM", "1") != "0" else asyncio.create_task(asyncio.sleep(0))
    async with make_checkpointer() as cp:
        runs.graphs(cp)
        yield
    warm_task.cancel()


app = FastAPI(title="GigBid API", version="0.1.0", lifespan=lifespan)
# Browser URLs use trailing slashes (Next `trailingSlash`); API URLs do not. Without this, Starlette redirects
# `/runs/<id>/` to the JSON API route and the static UI page never loads.
app.router.redirect_slashes = False
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


_SPA_ROOTS = {"jobs", "runs", "studio", "messages", "analytics", "settings", "pipeline", "login", "onboarding"}


@app.middleware("http")
async def spa_navigation(request: Request, call_next):
    """A browser NAVIGATING (Accept: text/html) to /jobs/<id>, /runs/<id>, /messages ... must get the web page, not the same-named JSON API route:
    Next links have no trailing slash, so a hard navigation used to land on the API ('detail: not authenticated'). fetch()/curl API calls are unaffected."""
    p = request.scope["path"]
    if request.method == "GET" and p.strip("/").split("/")[0] in _SPA_ROOTS and not p.endswith("/") and "text/html" in request.headers.get("accept", ""):
        request.scope["path"] = p + "/"
    return await call_next(request)


@app.middleware("http")
async def trace_id_mw(request: Request, call_next):
    """One trace id flows UI request -> API -> graph -> MCP servers -> audit log (x-trace-id header)."""
    tid = request.headers.get("x-trace-id") or new_trace_id()
    set_trace(tid)
    resp = await call_next(request)
    resp.headers["x-trace-id"] = tid
    return resp


for r in (auth, jobs, proposals, approvals, messages, run_routes, analytics, settings, memory):
    app.include_router(r.router)


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/health/tools")
async def health_tools():
    """Drives the 'marketplace unavailable' banner in the UI."""
    return get_hub().status()


@app.post("/admin/chaos/{server}/{state}")
async def chaos(server: str, state: str, user: dict = Depends(current_user)):
    """Demo/viva helper: simulate killing an MCP server (state=down|up). Authenticated users only."""
    hub = get_hub()
    (hub.disabled.add if state == "down" else hub.disabled.discard)(server)
    if state != "down":
        hub._mark(server, True)  # clear the stale "unavailable" mark so the banner disappears immediately on restore
    return hub.status()


class SPAStatic(StaticFiles):
    """Static export serving with a fallback for dynamic routes (/jobs/<id>, /studio/<id>, /runs/<id>) -> the prerendered `_` page."""

    async def get_response(self, path, scope):
        parts = path.replace("\\", "/").strip("/").split("/")
        if len(parts) >= 2 and parts[0] in ("jobs", "studio", "runs") and parts[1] != "_":
            # Serve the prerendered `_` page before static lookup: real ids can contain ':' (runs) which is
            # not a legal Windows filename, and a failed lookup would otherwise raise inside the thread pool.
            return await super().get_response(f"{parts[0]}/_/index.html", scope)
        return await super().get_response(path, scope)


_web = os.environ.get("WEB_DIST", "apps/web/out")
if os.path.isdir(_web):
    app.mount("/", SPAStatic(directory=_web, html=True), name="web")
