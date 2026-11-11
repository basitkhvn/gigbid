# HANDOFF: where the GigBid assignment stands (session stopped on user request)

Repo: https://github.com/basitkhvn/gigbid (PRIVATE; make public before submitting). Local: `~/Desktop/agentic assignment 2`. Due **12 Nov 2026 11:59 PM PKT**.
LLM: DeepSeek (`deepseek-flash`, `deepseek-v4-pro`), key in `.env` (gitignored). Python venv: `.venv` (3.11, `uv`). Run everything with `PYTHONPATH=.`.

## Context
- The starter kit had NO GigSim and NO persona data, so I built stand-ins: `gigsim_local/` (simulator), `data/generate.py` (synthetic personas, jobs, dev sets). Say this in the report. `gigsim/` holds only a README placeholder.
- The real 2 Nov "policy update" was not provided. I SIMULATED one (Connects x1.5, cover letter 200-1500 chars) in commit `b8a7d71` (9 lines, 3 files). Docs say it is simulated.
- Kaggle datasets were NOT used (documented in `docs/DATA_CARD.md`).

## Done (committed + pushed)
MCP servers (marketplace/portfolio/workspace) + ToolHub; RAG variants V0-V8 + v_best, claim verification; bid + conversation LangGraphs (parallel Send, interrupt approval, exactly-once executor, memory promotion rules); FastAPI (auth, inbox, SSE runs, approvals, pipeline, analytics, settings, memory); Next.js UI (`apps/web`) with 5 passing Playwright specs; worker (`worker/`); tests (24 pass: `make test`); CI workflows; docs (ARCHITECTURE, TOOLS, DATA_CARD, RUNBOOK, SAFETY, EXTENSION X2, CHANGE_REQUEST, AI_USAGE, adr/, HYPOTHESES); README with auto-spliced results; `render.yaml` + `infra/docker/single.Dockerfile` for deployment.

## Results so far (evals/results/*.json; older-config runs exist, final re-runs were in progress)
Retrieval Recall@5: V0 0.528 -> v_best 0.905 (shipped, rank without cross-encoder: 0.947). Plain hybrid V2 0.418 (< V0). Decomposition is the key component (0.456 without). Cross-encoder ranking HURTS recall (negative result). Decision F1 ~0.98 (synthetic gold, optimistic); scam recall 0.81 before low-budget rule fix. Injection ASR 0% even without defences (hypothesis falsified; weak attacks). Flash vs v4-pro: v4-pro ~5x cost, p95 210s vs 31s. Single ReAct agent vs supervisor vs graph: graph best on decision accuracy/grounding; single agent competitive on reply rate. Tool design: rewritten descriptions best.

## UPDATE: all final-config evals FINISHED and were committed (docs/RESULTS.md regenerated). Judge scores (step 1 first command) and traces still TODO.

## (old note) IN FLIGHT when stopped (may have died; results only write at end)
Final-config re-runs of: rag_eval, gigsim_outcomes, decision_eval, proposal_eval (open_flash, open_v4pro), agent_comparison, injection_eval. If `evals/results/*.json` are older than the last commit, re-run:
```
set -a; . ./.env; set +a; export PYTHONPATH=.
.venv/bin/python -m evals.runners.rag_eval --n 60
.venv/bin/python -m evals.runners.ablation --n 60
.venv/bin/python -m evals.runners.decision_eval
.venv/bin/python -m evals.runners.gigsim_outcomes --n 60
.venv/bin/python -m evals.runners.proposal_eval --profile open --n 8 --scam 2 --tag open_flash
.venv/bin/python -m evals.runners.proposal_eval --profile open_reasoner --n 8 --scam 2 --tag open_v4pro
.venv/bin/python -m evals.runners.agent_comparison --n 50
.venv/bin/python -m evals.runners.injection_eval --n 12
```
Run them ONE OR TWO AT A TIME (7 at once pushed load average to 148 and stalled everything).

## TODO (in order)
1. Finish/re-run evals above; then `python -m evals.runners.judge_calibration score-file evals/results/proposals_open_flash.json` (and open_v4pro); `python -m evals.runners.make_tables` (updates docs/RESULTS.md + README).
2. `python scripts/make_traces.py` -> docs/traces/ (scam skip, approved proposal, critic loop, crash-resume). Needs DEEPSEEK_API_KEY.
3. **YOU label 30 proposals** in `evals/datasets/judge_calibration_sheet.csv` (column human_score 1-5), then `judge_calibration judge` and `judge_calibration kappa`. Do NOT fabricate labels.
4. Write `docs/WRITEUP_DRAFT.md` (1200-1800 words; surprise: plain hybrid worse than dense, rerank hurt, same-project-three-ways crowding hurt replies) and publish it (LinkedIn/Medium). Add the link to README.
5. Write the R&D report (<=10 pages PDF; sections listed in the assignment PDF `docs/Assignment-II_AI-4016-GigBid.docx.pdf`); include failure taxonomy (>=10 failed dev jobs: see `evals/results/decision_eval*.json` failures; scam-miss fix example is documented), hidden-test section = "not available". Render HTML->PDF with Playwright chromium (already installed under apps/web).
6. Deploy: Render (`render.yaml`, set DEEPSEEK_API_KEY, APP_SECRET_KEY, REVIEWER_PASSWORD) or any Docker host with `infra/docker/single.Dockerfile`. Put live URL in README. Put reviewer login in the Google Classroom PRIVATE comment only.
7. Record 3-min demo video (inbox -> approved proposal; scam caught; injection ignored; client reply). Add link to README.
8. Make repo public (`gh repo edit basitkhvn/gigbid --visibility public --accept-visibility-change-consequences`), final commit BEFORE deadline, ZIP the source if requested.
9. Read all code for the viva (15 min live: kill marketplace MCP, crash/resume, evidence deletion, injection defence, style memory, live-mode switch, change-request diff). Review `docs/AI_USAGE.md` and make it true to your own review.

## Known honest gaps
Live Upwork adapter/OAuth never run; Google Calendar/Gmail = local mock; GitHub MCP wired not run; docker compose, Postgres, Redis/Arq paths untested; no public deployment; no human pairwise panel; judge uncalibrated until step 3; tracing is self-hosted JSONL (no Langfuse/LangSmith); UI mobile layout not verified on a device; USD prices in `agent/config.yaml` are placeholders.
