# AGENTS.md (read by OpenCode / other coding agents)

You are continuing a nearly finished university assignment (GigBid, AI-4016 R&D Assignment II). **The deadline is today.**

1. Read `docs/PROGRESS.md` FIRST, especially the section "UPDATE 2026-11-14". It lists what is done, what is running, and the remaining tasks in order.
2. Then skim `HANDOVER.md` (older) and `docs/ARCHITECTURE.md` only if needed.
3. Rules: never print or commit secrets (`.env` holds the Groq key); every number in docs must trace to a file in `evals/results/`; never fabricate results or human labels; keep negative results; commit small and push to `main`; end commit messages with a Co-Authored-By line for whichever agent made the change.
4. Run `PYTHONPATH=. .venv/Scripts/python.exe -m pytest -q` and `ruff check .` before pushing. Windows machine; use Git Bash or PowerShell syntax accordingly.
5. The owner is a student who must explain the system in a viva: keep changes small and explain them in plain language.
