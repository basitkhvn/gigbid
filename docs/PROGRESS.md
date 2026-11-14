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
