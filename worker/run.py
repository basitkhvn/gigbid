"""Windows launcher for the Arq worker (selector loop for psycopg). Linux/Docker: `arq worker.worker.WorkerSettings`."""
import asyncio
import sys

from arq.worker import run_worker

from worker.worker import WorkerSettings

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    run_worker(WorkerSettings)
