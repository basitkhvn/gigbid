# Résumé bullet (every number traces to a file in `evals/results/`)

- Built GigBid, a LangGraph multi-agent freelancer copilot (3 MCP servers, human-approval gate, crash-safe exactly-once submission): on a local Qwen3.5-4B, claim verification cut unsupported claims per proposal from 0.79 to 0.29, and the hand-built graph made the right bid/skip call on 16/16 test jobs vs 44% for a single ReAct agent at ~12x fewer tokens per job (3.7k vs 42.3k).
- Cut prompt-injection attack success from 35% to 4% with input/output defences, and showed evidence-grounded proposals earn a 73.9% vs 42.2% simulated reply rate (Fisher p < 1e-8, synthetic GigSim; caveat in `docs/DATA_CARD.md`).

Sources: `proposals_local_qwen.json`, `agent_comparison_local_qwen.json`, `injection_eval_local_qwen.json`, `ab_experiment.json`.
