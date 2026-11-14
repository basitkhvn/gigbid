"""Deploy GigBid to a free Hugging Face Space (Docker SDK, 16 GB RAM, public URL).

Usage (Windows/Git Bash):  .venv/Scripts/python.exe scripts/deploy_hf_space.py [space_name]
Reads from .env (never printed): HF_TOKEN (write token), GROQ_API_KEY, REVIEWER_PASSWORD (optional: generated if missing, then saved to .env).
Stages ONLY git-tracked files (no .env, no local data) into a temp dir, adds a Space Dockerfile + README front matter, uploads, sets Space secrets.
"""
from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import dotenv_values
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
env = {**dotenv_values(ROOT / ".env"), **{k: v for k, v in os.environ.items() if k in ("HF_TOKEN", "HF_ACCESS_TOKEN", "GROQ_API_KEY", "REVIEWER_PASSWORD")}}
token, groq = env.get("HF_TOKEN") or env.get("HF_ACCESS_TOKEN"), env.get("GROQ_API_KEY")
if not token or not groq:
    sys.exit("Need HF_TOKEN and GROQ_API_KEY in .env (HF_TOKEN = a Hugging Face *write* token from huggingface.co/settings/tokens).")
pw = env.get("REVIEWER_PASSWORD")
if not pw:
    pw = secrets.token_urlsafe(9)
    with open(ROOT / ".env", "a", encoding="utf-8") as f:
        f.write(f"\nREVIEWER_PASSWORD={pw}\n")
    print("Generated REVIEWER_PASSWORD and saved it in .env (look there; it is not printed here).")

api = HfApi(token=token)
user = api.whoami()["name"]
name = sys.argv[1] if len(sys.argv) > 1 else "gigbid"
repo_id = f"{user}/{name}"
api.create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True)

stage = Path(tempfile.mkdtemp(prefix="gb_space_"))
files = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
for rel in files:
    src = ROOT / rel
    if src.is_file() and not rel.startswith(("docs/report/", "evals/results/")) and "node_modules" not in rel:
        dst = stage / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
# keep small result files the app/docs may read
(stage / "evals" / "results").mkdir(parents=True, exist_ok=True)
for f in (ROOT / "evals" / "results").glob("*.json"):
    shutil.copy2(f, stage / "evals" / "results" / f.name)

df = (ROOT / "infra" / "docker" / "single.Dockerfile").read_text(encoding="utf-8")
df = df.replace("MODEL_PROFILE=open", "MODEL_PROFILE=groq").replace("EXPOSE 8000", "EXPOSE 7860").replace("${PORT:-8000}", "${PORT:-7860}")
df = df.replace("GIGBID_STATE_DIR=/state", "GIGBID_STATE_DIR=/tmp/state")  # Spaces: writable /tmp (state resets on restart)
(stage / "Dockerfile").write_text(df, encoding="utf-8")
(stage / "README.md").write_text(
    "---\ntitle: GigBid\nemoji: 💼\ncolorFrom: indigo\ncolorTo: blue\nsdk: docker\napp_port: 7860\npinned: false\n---\n\n"
    "GigBid, a multi-agent freelancer copilot (AI-4016 R&D Assignment II). Source: https://github.com/basitkhvn/gigbid\n", encoding="utf-8")

api.upload_folder(folder_path=str(stage), repo_id=repo_id, repo_type="space", commit_message="Deploy GigBid")
api.add_space_secret(repo_id, "GROQ_API_KEY", groq)
api.add_space_secret(repo_id, "REVIEWER_PASSWORD", pw)
api.add_space_secret(repo_id, "APP_SECRET_KEY", secrets.token_urlsafe(32))
api.add_space_variable(repo_id, "REVIEWER_EMAIL", "reviewer@gigbid.demo")
print(f"Uploaded. Build takes ~10-15 min. Space page: https://huggingface.co/spaces/{repo_id}")
print(f"Live URL (once built): https://{user.lower()}-{name.lower()}.hf.space")
