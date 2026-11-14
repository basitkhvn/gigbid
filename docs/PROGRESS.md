# PROGRESS (read this first when resuming; newer than HANDOVER.md section 5)

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
