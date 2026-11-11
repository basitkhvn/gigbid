# ADR 3: Rules, thresholds, models and prompts live in files
Models per node, budgets, thresholds and platform rules (`platform_rules`) are in `agent/config.yaml`; prompts are versioned files in `agent/prompts/`. **Why:** the 2 Nov policy change was absorbed with 9 changed lines in 3 files and zero Python logic changes (docs/CHANGE_REQUEST.md).
