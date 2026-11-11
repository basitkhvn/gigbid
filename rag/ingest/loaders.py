"""B1 ingestion: loaders (JSONL corpus, Markdown, PDF CVs, GitHub README via the GitHub MCP tool hub),
chunkers and incremental indexing. Every chunk carries metadata: persona, type, project, skills, date,
industry and (for proposals) outcome."""
from __future__ import annotations

import json
import os
from pathlib import Path

from agent.config import ROOT

PERSONA_DIR = ROOT / "data/personas"


def user_items_path(persona: str) -> Path:
    d = Path(os.environ.get("GIGBID_STATE_DIR", ROOT / "data/processed")) / "user_items"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{persona}.jsonl"


def load_items(persona: str) -> list[dict]:
    p = PERSONA_DIR / persona / "items.jsonl"
    items = [json.loads(line) for line in p.read_text().splitlines() if line]
    extra = user_items_path(persona)  # items users added via the UI (kept out of the repo)
    if extra.exists():
        items += [json.loads(line) for line in extra.read_text().splitlines() if line]
    return items


def load_markdown(path: Path, persona: str, type_: str = "case_study") -> dict:
    text = path.read_text()
    return {"id": f"{persona}-md-{path.stem}", "persona": persona, "type": type_, "title": path.stem, "text": text,
            "skills": [], "project": path.stem, "industry": None, "date": None}


def load_pdf(path: Path, persona: str) -> dict:
    from pypdf import PdfReader
    text = "\n".join(pg.extract_text() or "" for pg in PdfReader(str(path)).pages)
    return {"id": f"{persona}-pdf-{path.stem}", "persona": persona, "type": "cv", "title": path.stem, "text": text,
            "skills": [], "project": None, "industry": None, "date": None}


async def load_github_readme(hub, persona: str, owner: str, repo: str) -> dict:
    """Ingest a repo README through the third-party GitHub MCP server (never direct HTTP)."""
    res = await hub.call("ingest", "github_get_file_contents", {"owner": owner, "repo": repo, "path": "README.md"})
    return {"id": f"{persona}-gh-{repo}", "persona": persona, "type": "readme", "title": repo, "text": str(res),
            "skills": [], "project": repo, "industry": None, "date": None}


def add_user_item(persona: str, item: dict) -> None:
    """Incremental re-index entry point: append, then callers re-index only this item."""
    item = {**item, "persona": persona}
    with user_items_path(persona).open("a") as f:
        f.write(json.dumps(item) + "\n")


def chunk(item: dict, size: int = 300, overlap: int = 60) -> list[dict]:
    """Fixed-size character chunks (V0). Short items stay whole."""
    t = item["text"]
    if len(t) <= size:
        return [{**item, "chunk_id": f"{item['id']}#0", "chunk_text": t}]
    out, i, n = [], 0, 0
    while i < len(t):
        out.append({**item, "chunk_id": f"{item['id']}#{n}", "chunk_text": t[i:i + size]})
        i += size - overlap
        n += 1
    return out
