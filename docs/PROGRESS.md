# PROGRESS (read this first when resuming)

## >>> CURRENT STATE (updated 2026-11-14 14:10; the dated "UPDATE" sections further down are history; this block wins on any conflict) <<<
**Deadline: 2026-11-14 (today when written). Prioritise submission items over polish.**

### Where everything is
- Repo (public): https://github.com/basitkhvn/gigbid, branch `main`, history scanned: no secrets. `.env` is gitignored and holds `GROQ_API_KEY`, `REVIEWER_PASSWORD`, `HF_ACCESS_TOKEN` (never print/commit them).
- Report: `docs/report/report.html` -> `docs/report/GigBid_RD_Report.pdf` (6 pages, A4, includes section 11 with local-Qwen, Groq and F3 results). Regenerate PDF after edits with headless Edge: `msedge --headless=new --no-pdf-header-footer --print-to-pdf=docs/report/GigBid_RD_Report.pdf file:///.../report.html`, then commit the PDF.
- Evals (all in `evals/results/`): local Qwen3.5-4B (`*_local_qwen*.json`), Qwen3-8B (`proposals_local_qwen3_8b.json`), Groq Qwen3.8-27B (`proposals_groq_qwen.json`), F3 rewrite test (`proposals_local_qwen_f3.json`: no benefit, kept OFF; default stays `GIGBID_REPAIR_MODE=delete`). DeepSeek result files are untouched.
- Models/profiles in `agent/config.yaml`: `open` (DeepSeek, needs a key we do not have), `groq` (hosted open-weight Qwen on Groq free tier, used for deployment), `local_qwen` (Ollama, qwen3.5:4b), `offline`.

### Deployment (DECISION: backend stays on the owner's laptop; Render/HF/Vercel abandoned)
- The owner chose to keep the backend on this laptop behind a public tunnel (no card needed anywhere). A Render free service (https://gigbid-99lo.onrender.com) was tried and kept hitting the 512 MB memory limit (a full job peaks ~430 MB on the laptop copy); it is NOT the submitted link and can be deleted/suspended in the Render dashboard. Do not spend more time on it.
- Start/keep alive: `powershell -NoProfile -ExecutionPolicy Bypass -File "<repo>\scripts\serve_public.ps1"` (quote the path, it contains a space). It starts the API on port 8001 (`MODEL_PROFILE=groq`, serves `apps/web/out`), opens the tunnel, and then SUPERVISES both (checks every 20 s, restarts whatever died; log `.logs\supervisor.log`; current URL in `.logs\public_url.txt`). Sleep/hibernate on AC are disabled by the script.
- FIXED URL IS NOW ACTIVE: https://chicly-unhesitative-jamila.ngrok-free.dev (ngrok free static domain; `NGROK_AUTHTOKEN`/`NGROK_DOMAIN` are in .env; ngrok was updated to 3.39.13 because 3.3.1 gave ERR_NGROK_121; script uses `--domain=`). This is the SUBMITTED live URL; README row filled. Browsers see ngrok's free interstitial once ("Visit Site"); API calls can send the header `ngrok-skip-browser-warning: 1`. Tunnel options: Cloudflare quick tunnel by default (random URL, CHANGES whenever cloudflared restarts; current: https://artist-vista-restrict-chamber.trycloudflare.com). For a FIXED URL: free ngrok account (no card) -> add `NGROK_AUTHTOKEN=...` and `NGROK_DOMAIN=<your-free-static-domain>.ngrok-free.app` to `.env`, then restart the script; it then uses ngrok with that fixed domain (ngrok is installed).
- The laptop must stay on, plugged in and online until grades are released. A login-time auto-start task was NOT registered (blocked by the sandbox); owner can run once: `schtasks /create /f /tn GigBidServe /sc onlogon /tr "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"<repo>\scripts\serve_public.ps1\""`.
- UI build (needed once, already built): `cd apps/web; $env:STATIC_EXPORT=1; $env:NEXT_PUBLIC_API_URL=""; npx next build` (the npm script fails on Windows). Tested through the tunnel: /health, UI, `POST /auth/login`, one job to `awaiting_approval` on Groq.
- Another uvicorn on port 8000 (started 13:50 by something other than the main session, probably OpenCode's demo run) exists; do not kill it blindly. Hosts that need a card/PRO: HF Docker Spaces (`scripts/deploy_hf_space.py` kept but dead), Koyeb, Fly.io, Oracle/GCP.
- Fixed deploy-breaking bug earlier: `pyproject.toml` runtime deps were incomplete.

### UI bugs fixed ~15:00 (found while preparing the demo)
- Analytics crashed ("client-side exception"): `useApi` reported loading=false with data=null on the first render after auth; fixed in `apps/web/src/lib/hooks.tsx`.
- Fresh loads/refresh of /jobs/<id>/, /studio/<id>/, /runs/<id>/ used the static-export placeholder id `_` (job not found / run not found); fixed with `useRouteId()` (reads the id from the URL). The UI must be REBUILT after UI changes: `cd apps/web; $env:STATIC_EXPORT=1; $env:NEXT_PUBLIC_API_URL=""; npx next build` (the live API serves `apps/web/out` from disk, no restart needed).
- Someone had left the marketplace chaos toggle on ("Simulate marketplace outage" amber banner): restore with the nav button or `POST /admin/chaos/marketplace/up`. After the demo make sure it says "Simulate marketplace outage" (= up).

- Clicking a job / Draft proposal showed raw JSON `{"detail":"not authenticated"}`: Next `<Link>` hrefs have no trailing slash and `/jobs/<id>`, `/runs/<id>` etc. are ALSO API routes. Fixed with the `spa_navigation` middleware in `apps/api/main.py` (GET + `Accept: text/html` on SPA roots gets the page; fetch/curl unchanged). Always test by CLICKING through the app (Playwright scripts that `goto` typed URLs missed this).
- "Simulate marketplace outage" button was unreliable: `ToolHub.status()` let a stale stored `ok` overwrite the computed one (fixed in `agent/mcp_client.py`), restore now clears the stale failure mark (`apps/api/main.py`), and `Shell.tsx` ignores health polls that started before the last toggle.

### What the OWNER still has to do (an agent cannot)
1. Make sure the laptop stays on and run `serve_public.ps1`; optionally set up the fixed ngrok domain; use the URL in `.logs\public_url.txt` as the submitted live URL (re-check it right before submitting).
2. Record the 3-minute demo video (inbox -> approved proposal; scam caught; injection ignored; client reply). OpenCode may automate a Playwright screen recording + write `docs/DEMO_SCRIPT.md`; the owner records voice-over (Clipchamp) and uploads to YouTube as Unlisted.
3. DONE: write-up published on dev.to: https://dev.to/abdul_basit_863d2936a69df/the-retriever-with-the-best-score-wrote-the-worst-proposals-and-other-things-my-ablations-told-me-20ne (README row filled; plain-text copy in `docs/WRITEUP_PLAIN.txt`).
4. Portfolio MCP "publication": cite `mcp_servers/portfolio` in the public repo (PyPI optional, not done).
5. Submit on Google Classroom: deployed URL, reviewer login in a PRIVATE comment only (reviewer@gigbid.demo + the REVIEWER_PASSWORD in `.env`), repo link, report PDF, video link, MCP + write-up links. Confirm the new deadline.
6. Optional: judge calibration labels (`evals/datasets/judge_calibration_sheet.csv`, owner-only, never fabricate), a fixed ngrok address for the tunnel.

### What an AGENT should do next
- Verify the laptop deployment (read `.logs\public_url.txt`, test `/health` and the reviewer login through that URL).
- When the owner supplies URLs, fill the TODO rows at the top of `README.md` (live app, demo video, write-up, Portfolio MCP), commit, push. Keep the README caveats honest.
- Do NOT flip the F3 default to rewrite; do not report numbers that are not in `evals/results/`; never commit secrets; commit small with a Co-Authored-By line.

### Machine notes (Windows)
Ollama models in `D:\ollama\models` (start the server with `OLLAMA_MODELS=D:\ollama\models`, `OLLAMA_CONTEXT_LENGTH=8192`); currently stopped. 16 GB RAM is tight: close browsers, one heavy job at a time. Python: `.venv\Scripts\python.exe` with `PYTHONPATH=.`; load keys in bash with `set -a; . ./.env; set +a`. gh CLI: `C:\Program Files\GitHub CLI\gh.exe` (logged in as basitkhvn). opencode is installed (`opencode -m opencode/deepseek-v4.1-flash-free` in the repo folder).

---

Machine: Windows, RTX 3070 Laptop 8 GB, 16 GB RAM. Models live in `D:\ollama\models` (qwen3:8b, qwen3.5:4b). Ollama must be started with
`OLLAMA_MODELS=D:\ollama\models` and `OLLAMA_CONTEXT_LENGTH=8192`. Python env: `.venv` (uv, Python 3.11). Always `PYTHONPATH=.`.
Memory is tight: run ONE eval at a time, close browsers/Spotify first. `qwen3:8b` kept getting OOM-killed, so the shipped local profile is `qwen3.5:4b`.

## Done
- Environment, deps, tests green (`pytest -q`), `ruff check .` clean.
- Local Qwen via Ollama works. `agent/llm.py` sends `reasoning_effort: none` for Ollama (thinking off).
- Fixed: packaging (`[tool.setuptools] packages = []`), parallel-branch `status` crash (reducer in `agent/state.py`), eval runners now model-agnostic with tagged result files (DeepSeek result files untouched).
- Evals on `qwen3.5:4b` (profile `local_qwen`), files in `evals/results/`:
  - `proposals_local_qwen.json` (30 jobs, 24 drafted): unsupported/proposal 0.79 -> 0.29, reply 0.708, hire 0.208, p50 106 s, p95 445 s, 4766 tok/job.
  - `proposals_local_qwen3_8b.json`: earlier run on qwen3:8b (30 jobs, 12 drafted): unsupported 1.33 -> 0.25, p50 183 s. Extra data point only.
  - `agent_comparison_local_qwen.json` (n=16, same model for all): bid/skip acc graph 1.00, supervisor 0.50, single ReAct 0.44; scams wrongly bid 0/2/2; tokens/job 3664 / 5625 / 42334. Baseline usd was corrected 0.0 post-hoc (see `note` in file).
  - `injection_eval_local_qwen.json`: ASR 0.353 with no defence, 0.042 with input defence, 0.042 with input+output (small local model is genuinely injectable; DeepSeek run had ASR 0 because attacks were weak).
  - `tool_design_local_qwen.json` (40 tasks): selection/args acc fine 0.975/0.950, coarse 0.950/0.675, shipped best 1.0/0.975.
- F3 fix implemented: `rag/verify.py::repair(..., evidence)` rewrites unsupported sentences from cited evidence instead of deleting; enabled by env `GIGBID_REPAIR_MODE=rewrite` (default is still `delete`). Unit test `test_f3_rewrite_keeps_letter_instead_of_emptying_it`.

## In flight / remaining (in order)
1. F3 measurement: `GIGBID_REPAIR_MODE=rewrite python -m evals.runners.proposal_eval --profile local_qwen --n 8 --scam 2 --tag local_qwen_f3` -> `evals/results/proposals_local_qwen_f3.json`. Compare with `proposals_local_qwen.json` (n_drafted, unsupported after, letters emptied). If not worse, make `rewrite` the default in `agent/nodes/verifier.py`. Report the real outcome either way (class F3 in the report failure table).
2. `python -m evals.runners.make_tables` (regenerates `docs/RESULTS.md`; check it picks up the `*_local_qwen*` files, extend it if not).
3. `python scripts/make_traces.py` with `MODEL_PROFILE=local_qwen` -> `docs/traces/`.
4. Update docs/report with Qwen numbers (sections 3, 5, 10 of `docs/report/report.html`), mention honest caveats: n=16 for the comparison, 8k vs 4k context history, latency over the 60 s budget on a laptop GPU, local model cost = 0, DeepSeek rows kept. Update `docs/DATA_CARD.md` / README where they name DeepSeek as the only model. Re-render PDF (needs Node: `winget install OpenJS.NodeJS.LTS`, then `cd apps/web && npm ci && npx playwright install chromium`; node script with `page.pdf`, A4, <= 10 pages).
5. `pytest -q`, `ruff check .`, `python scripts/check_repo_rules.py`, commit (end message with the Co-Authored-By line), push.

## Owner-only (cannot be done by an agent)
- Hand-label 30 rows in `evals/datasets/judge_calibration_sheet.csv` (`human_score` 1-5), then `judge_calibration judge` / `kappa`.
- Record the 3-minute demo video; publish the write-up (`docs/WRITEUP_DRAFT.md`) and add the link to README; deploy (a hosted deploy cannot use the local GPU: use an API provider or a tunnel and say which); make the repo public; reviewer login only in the private Classroom comment; viva prep (`docs/ARCHITECTURE.md`, `agent/graphs/bid_graph.py`, `docs/AI_USAGE.md`). Confirm the new deadline date.

## Rules that still apply
Every number must trace to a file in `evals/results/`; never fabricate labels or results; keep negative results; human approval before anything is sent.

## UPDATE 2026-11-14 ~13:15 (latest; supersedes anything above that conflicts)
**DEADLINE IS TODAY (2026-11-14). Prioritise submission items over polish.**
- Repo is PUBLIC (https://github.com/basitkhvn/gigbid), history scanned: no secrets. `.env` is gitignored and holds `GROQ_API_KEY` (never print/commit it).
- New hosted open-weight profile `groq` (Qwen `qwen/qwen3.8-27b` on Groq free tier) in `agent/config.yaml`; `render.yaml` now deploys with `MODEL_PROFILE=groq` + secret `GROQ_API_KEY`. Provider option `reasoning_off: true` sends `reasoning_effort: none`.
- Groq eval `evals/results/proposals_groq_qwen.json` (30 jobs, 24 drafted): unsupported 0.67 -> 0.00, reply 0.50, hire 0.208, p50/p95 17.9/22.7 s (within the 60 s budget). tokens/job 274 looks too low vs local 4766: unverified, flagged in the report (do not use for token claims).
- Report `docs/report/report.html` has section 11 (local Qwen + Groq replication); PDF regenerated with headless Edge (6 pages, A4): `msedge --headless=new --no-pdf-header-footer --print-to-pdf=docs/report/GigBid_RD_Report.pdf file:///.../report.html`. Re-run this after any report edit and `git add` the PDF.
- Last pushed commit: 5db8491.

### Still running when this was written
- F3 measurement (local, `GIGBID_REPAIR_MODE=rewrite`, tag `local_qwen_f3`) -> `evals/results/proposals_local_qwen_f3.json`. When it exists: compare to `proposals_local_qwen.json` (n_drafted, unsupported after, emptied letters). Add 1 paragraph + the result to report section 11 / failure table class F3, replace the "Fix F3" bullet in "Limits and next steps", regenerate the PDF, commit, push. If not worse, flip the default in `agent/nodes/verifier.py` to `rewrite`. If the file never appears (process killed), skip it and say in the report that F3 is implemented and unit-tested but not re-measured.

### Remaining TODO (owner = the human; agent = you)
1. OWNER: deploy on Render (New > Blueprint > this repo). Secrets: `GROQ_API_KEY`, `REVIEWER_PASSWORD`. Agent helps only if the build log shows an error (ask the owner to paste it). Note `plan: starter` in render.yaml costs money; embeddings need >512 MB RAM. If the owner can't pay, make a lighter config (smaller embedding model or `GIGSIM_INPROCESS=1` single service) and say so honestly.
2. OWNER: record 3-min demo video (inbox -> approved proposal; scam caught; injection ignored; client reply). Publish write-up from `docs/WRITEUP_DRAFT.md` (1200-1800 words) on LinkedIn/Medium. Portfolio MCP "publication": cite `mcp_servers/portfolio` in the public repo (PyPI optional).
3. AGENT: when the owner gives the URLs, fill the TODO rows at the top of `README.md` (live app, demo video, write-up, Portfolio MCP), commit, push.
4. OWNER: submit on Google Classroom: deployed URL, reviewer login (PRIVATE comment only, never in repo), repo link, report PDF, video link, MCP + write-up links.
5. OPTIONAL (skip if short on time): `make_tables`, `scripts/make_traces.py`, judge calibration labels (owner-only, never fabricate).

## Machine notes (Windows)
Ollama: `OLLAMA_MODELS=D:\ollama\models`, models qwen3:8b, qwen3.5:4b; server must be started with that env var. RAM is tight (16 GB): close browsers, run ONE heavy job at a time. Use `.venv\Scripts\python.exe` with `PYTHONPATH=.`; load keys with `set -a; . ./.env; set +a` in bash. gh CLI: `C:\Program Files\GitHub CLI\gh.exe` (logged in as basitkhvn). Git author is already configured locally.

## UPDATE ~13:30: F3 measured
`proposals_local_qwen_f3.json` done. F3 rewrite did NOT help on Qwen3.5-4B (unsupported after 0.50 vs 0.29; reply 0.50 vs 0.71; baseline emptied 0/24 letters so F3 did not occur). Default stays `delete`. Report section 11 + limits updated and PDF regenerated. DO NOT flip the default to rewrite. Remaining work is only the OWNER tasks and README links (see list above).

## UPDATE ~13:45: DEPLOY PLAN CHANGED -> Hugging Face Space (free, 16 GB RAM), not Render
- Render starter costs money and Vercel cannot host this Python+embedding backend. Use `scripts/deploy_hf_space.py`.
- Fixed a deploy-breaking bug: `pyproject.toml` was missing runtime deps (numpy, fastembed, qdrant-client, ...) that the Dockerfile installs from; now listed.
- Owner steps: create a free account at huggingface.co, create a WRITE token (settings/tokens), add the line `HF_TOKEN=...` to `.env` (never commit/print it). Then run: `.venv/Scripts/python.exe scripts/deploy_hf_space.py gigbid`.
  The script stages only git-tracked files, adds a Space Dockerfile (port 7860, MODEL_PROFILE=groq) + README front matter, uploads, and sets Space secrets (GROQ_API_KEY from .env, REVIEWER_PASSWORD from .env or generated and saved to .env, APP_SECRET_KEY random). Reviewer email: reviewer@gigbid.demo. Build takes ~10-15 min; live URL is printed (https://<hfuser>-gigbid.hf.space).
- After deploy: open the URL, log in as the reviewer, run one job end to end. Space filesystem is ephemeral (`/tmp/state`), state resets on restart: fine for a demo, mention it. Put the URL in README (top table) and the Classroom submission; reviewer login only in the private Classroom comment.

## UPDATE ~14:20: DEPLOY = laptop + Cloudflare quick tunnel (no card needed anywhere else)
- Render and Hugging Face Docker Spaces need a card/PRO; HF script `scripts/deploy_hf_space.py` is kept but unusable on the free tier.
- Run: `powershell -ExecutionPolicy Bypass -File scripts\serve_public.ps1` (starts the API on port 8001 with `MODEL_PROFILE=groq`, serves the static UI from `apps/web/out`, opens a `trycloudflare.com` tunnel, prints the URL, saves it to `.logs/public_url.txt`). Needs the UI built first: `cd apps/web; $env:STATIC_EXPORT=1; $env:NEXT_PUBLIC_API_URL=""; npx next build` (the npm script `STATIC_EXPORT=1 next build` fails on Windows).
- Tested through the tunnel on 2026-11-14: /health 200, UI 200, reviewer login (`POST /auth/login`, email reviewer@gigbid.demo, password = REVIEWER_PASSWORD in .env) 200, one job draft reached `awaiting_approval` using Groq.
- WARNING: the quick-tunnel URL changes every time cloudflared restarts, and the laptop must stay on and online until grades are released. A fixed address needs an ngrok free account (static domain) or a Cloudflare named tunnel.
- Another uvicorn (started 13:50, not by this session, likely OpenCode's demo-recording run) occupies port 8000; do not kill it blindly.
- Vercel front-end (optional, requested by owner): build the UI with `NEXT_PUBLIC_API_URL=<tunnel URL>` and deploy `apps/web/out` with the Vercel CLI; needs the owner's Vercel login/token. The tunnel URL alone already serves the full app.

## UPDATE ~14:50: Render free deploy (https://gigbid-99lo.onrender.com)
- Render service exists (Blueprint from this repo, Free plan, 512 MB / 0.1 CPU, secrets GROQ_API_KEY + REVIEWER_PASSWORD set by the owner). First deploy crash-looped (silent restarts = OOM): the startup warm-up embedded all 3 persona corpora.
- Fix pushed: `GIGBID_WARM=0` skips the warm-up (apps/api/main.py); `infra/docker/single.Dockerfile` bakes the models (`FASTEMBED_CACHE_PATH=/app/.fastembed`) and the embedding cache at BUILD time. The owner must click Manual Deploy > Deploy latest commit on Render (public-URL blueprints do not auto-deploy).
- After the redeploy: test `/health`, `POST /auth/login` (reviewer@gigbid.demo + REVIEWER_PASSWORD), `POST /jobs/job-ml-0006/draft`, then `GET /runs/bid:<user>:job-ml-0006` until `awaiting_approval`. If it still dies: read Render Logs (look for killed/OOM), consider lowering memory further (disable the reranker via config) or fall back to the laptop tunnel (`scripts/serve_public.ps1`).
