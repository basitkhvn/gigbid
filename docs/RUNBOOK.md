# Runbook

## Run locally (no Docker)
```
make install                      # uv venv + deps (Python 3.11)
cp .env.example .env              # add DEEPSEEK_API_KEY for the open profile (never commit .env)
make seed                         # regenerate synthetic data (already committed)
REVIEWER_PASSWORD='choose-one' make demo     # API on :8000 with a reviewer@gigbid.demo login (persona: ml)
cd apps/web && npm install && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev   # UI on :3000 (set CORS_ORIGINS for the API)
make test                         # unit + MCP + contract + integration (offline profile, no API key needed)
make eval                         # LLM-free evals; make eval-llm needs DEEPSEEK_API_KEY
```
No key? `MODEL_PROFILE=offline` runs every node on its rule-based path (used by CI).

## Docker
`docker compose -f infra/docker-compose.yml up --build` (web :3000, api :8000). Status: written, **not verified end-to-end here**.

## Scheduling
Each saved search has an interval (60-1440 min, default 240). The worker ticks every 5 minutes and runs due searches; a search is "claimed" (last_run written) before it runs, so a crash never double-runs it, and jobs are de-duplicated by fingerprint so a restart never double-analyses. **Live mode interval:** the Upwork adapter refuses reads closer than 30 s per user and the recommended saved-search interval is >= 4 h: a human freelancer checks a feed a few times per day, and anything tighter looks like scraping.

## Failure drills (viva)
* Kill the marketplace MCP server: `POST /admin/chaos/marketplace/down` (UI nav toggle) or stop the container. Tool calls raise `ToolUnavailable`; runs become `queued_unavailable`; UI banner shows via `/health/tools`; restore and re-run (the run thread resumes from its checkpoint).
* Crash during approval: stop the API with a run `awaiting_approval`, restart, `GET /approvals` still lists it (read from the checkpoint), approve -> submitted once (`tests/integration/test_graphs.py`).
* Replay any job from any node: `GET /runs/{id}/history`, `POST /runs/{id}/replay/{checkpoint_id}`.

## Secrets
Only from environment. `.env.example` lists every variable. Reviewer credentials go in the Google Classroom private comment, not the repo.
