# AI usage

**Tool:** Claude Code (Claude Sonnet 5.5), used interactively for most of the implementation: data generator, simulator, MCP servers, RAG variants, graphs, API, eval runners, tests, docs. A forked Claude Code subagent wrote the Next.js frontend and Playwright specs (`apps/web/`). DeepSeek (`deepseek-flash`, `deepseek-v4-pro`) is the runtime LLM, not a coding tool.

**Accountability note for the author:** you must be able to explain and change every part in the viva. Read the code; this file is a draft of what happened, edit it to be true to your own review.

## Things the assistant got wrong that were caught (by tests/measurement)
1. **Swallowed the approval interrupt.** The generic node wrapper caught every `Exception`, including LangGraph's interrupt (`GraphBubbleUp`), so the graph never paused for approval and later crashed with `KeyError: 'approval'`. Found in the first end-to-end run; fixed by re-raising `GraphBubbleUp` (`agent/nodes/common.py`).
2. **Treated past proposals as proof of experience.** The first Fit Matcher cited the persona's own old proposals as evidence; those are unverified marketing text. Now restricted to case studies, READMEs, reviews and CV (`agent/nodes/fit_matcher.py`).
3. **Predicted that cross-encoder reranking would help; measurement said it hurts ranking** (Recall@5 0.905 with rerank-ranking vs 0.947 without). The shipped pipeline ranks without it and keeps it only as an absolute-relevance gate (`evals/results/ablation*.json`).
4. **Per-call MCP sessions burned CPU** (found by the frontend subagent's Playwright runs: uvicorn at ~400% CPU). Replaced by one persistent in-memory session per server.
5. **A hung eval.** DeepSeek keeps connections alive under load so per-read timeouts never fired and an eval hung for ~30 minutes; added a hard wall-clock deadline and moved LLM calls off the event loop.
6. A first "evidence-grounded vs generic" A/B *lost* (0.19 vs 0.42 reply); root cause was top-5 *items* repeating one project, not the idea (see EXTENSION.md). Reported, not hidden.
7. A regex in config (`+\d{6,}`) was invalid and crashed Compliance; caught by the end-to-end run.

## Files by tool
Everything under `apps/web/` -> subagent; everything else -> Claude Code in the main session, reviewed through tests and eval runs.
