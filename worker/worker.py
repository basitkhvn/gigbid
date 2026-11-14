"""Arq worker (Redis). Runs the scheduled scout tick every 5 minutes and long agent runs outside web requests.
Start: `arq worker.worker.WorkerSettings`.  When REDIS_URL is unset the API falls back to in-process asyncio tasks (dev/free hosts)."""
from __future__ import annotations

import os

from arq import cron
from arq.connections import RedisSettings

from agent.checkpointer import make_checkpointer
from apps.api import runs
from worker.scout import scout_due


async def startup(ctx):
    ctx["cp_cm"] = make_checkpointer()
    cp = await ctx["cp_cm"].__aenter__()
    runs.graphs(cp)


async def shutdown(ctx):
    await ctx["cp_cm"].__aexit__(None, None, None)


async def scout_tick(ctx):
    return await scout_due()


async def run_bid_job(ctx, user: dict, job: dict):
    """Idempotent: arq _job_id = run id, so a retry/restart never starts the same job twice; the graph thread resumes from its checkpoint."""
    return runs.start_bid(user, job, from_queue=True)


class WorkerSettings:
    functions = [run_bid_job]
    cron_jobs = [cron(scout_tick, minute=set(range(0, 60, 5)))]
    on_startup, on_shutdown = startup, shutdown
    redis_settings = RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    max_tries = 3
