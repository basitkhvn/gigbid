"""Windows launcher: psycopg's async Postgres driver cannot run on the default Proactor loop, so serve on a selector loop.
Linux/Docker deployments just use `uvicorn apps.api.main:app`."""
import asyncio
import os
import sys

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("GIGBID_PORT", "8002"))
    server = uvicorn.Server(uvicorn.Config("apps.api.main:app", host="127.0.0.1", port=port))
    loop = asyncio.SelectorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.serve())
