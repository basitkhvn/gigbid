from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PERSONAS = ["ml", "web", "data"]
RESULTS = ROOT / "evals/results"


def dev(persona: str) -> list[dict]:
    return [json.loads(l) for l in (ROOT / f"evals/datasets/dev_{persona}.jsonl").read_text().splitlines() if l]


def write(name: str, obj) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / name
    p.write_text(json.dumps(obj, indent=1, default=str))
    return p


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None


def pct(xs, q):
    xs = sorted(xs)
    return round(xs[int(q * (len(xs) - 1))], 3) if xs else None
