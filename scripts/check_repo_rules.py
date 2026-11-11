"""CI-enforced repo rules: no secrets, gigsim/ untouched, every prompt lives in agent/prompts/, results tables up to date."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []
tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()

# 1. secrets
SECRET = re.compile(r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
for f in tracked:
    p = ROOT / f
    if p.suffix in {".png", ".jpg", ".pdf", ".lock", ".npy", ".sqlite"} or "node_modules" in f or not p.is_file():
        continue
    try:
        if SECRET.search(p.read_text(errors="ignore")):
            errors.append(f"possible secret in {f}")
    except Exception:  # noqa: BLE001
        pass
if ".env" in tracked:
    errors.append(".env is tracked")

# 2. gigsim/ holds only the placeholder README (official simulator must not be edited by students)
extra = [f for f in tracked if f.startswith("gigsim/") and f != "gigsim/README.md"]
if extra:
    errors.append(f"unexpected files under gigsim/: {extra}")

# 3. no inline prompts in agent code
for f in tracked:
    if f.startswith("agent/") and f.endswith(".py"):
        txt = (ROOT / f).read_text()
        if re.search(r'"""You are |"You are a|\'You are a', txt):
            errors.append(f"inline prompt in {f}: move it to agent/prompts/")

# 4. results table is regenerated from evals/results (numbers in docs trace to files)
before = (ROOT / "docs/RESULTS.md").read_text() if (ROOT / "docs/RESULTS.md").exists() else ""
subprocess.run([sys.executable, "-m", "evals.runners.make_tables"], cwd=ROOT, check=True, capture_output=True)
after = (ROOT / "docs/RESULTS.md").read_text()
if before != after:
    errors.append("docs/RESULTS.md is stale: run `python -m evals.runners.make_tables` and commit")

if errors:
    print("\n".join(errors)); sys.exit(1)
print("repo rules OK")
