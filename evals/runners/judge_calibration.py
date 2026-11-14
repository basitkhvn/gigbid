"""LLM-judge calibration (B4). Workflow:
  1. python -m evals.runners.judge_calibration make-sheet   -> evals/datasets/judge_calibration_sheet.csv (30 anonymised proposals)
  2. YOU label the `human_score` column (1-5) WITHOUT looking at judge scores.
  3. python -m evals.runners.judge_calibration judge        -> adds LLM judge scores (evals/results/judge_scores.json)
  4. python -m evals.runners.judge_calibration kappa        -> Cohen's kappa (binary good>=4 and quadratic-weighted) + disagreements
  `score-file <proposals_*.json>` scores a proposals file with the judge for the results table."""
from __future__ import annotations

import csv
import json
import random
import sys

from agent.llm import complete_json, prompt
from evals.common import RESULTS, ROOT, dev, mean, write

SHEET = ROOT / "evals/datasets/judge_calibration_sheet.csv"


def judge_one(job_title, reqs, text):
    out = complete_json("critic", prompt("judge"), f"JOB: {job_title}\nREQUIREMENTS: {reqs}\n\nPROPOSAL:\n{text}")
    return int(out["score"]) if out and str(out.get("score", "")).isdigit() else None


def make_sheet():
    rnd = random.Random(7)
    items = []
    for tag in ("open_flash", "open_v4pro"):
        p = RESULTS / f"proposals_{tag}.json"
        if p.exists():
            for r in json.loads(p.read_text())["jobs"]:
                if r.get("text"):
                    items.append({"src": tag, "job": r["job"], "text": r["text"]})
    from evals.runners.gigsim_outcomes import letter_generic  # generic-style letters give the judge a clear contrast
    allj = {j["job_id"]: j for p in ("ml", "web", "data") for j in dev(p)}
    for jid in rnd.sample(sorted(k for k, v in allj.items() if v["gold"]["kind"] == "good"), 12):
        j = allj[jid]
        items.append({"src": "generic_template", "job": jid, "text": letter_generic(j["gold"]["persona"], j)})
    rnd.shuffle(items)
    items = items[:30]
    with open(SHEET, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "job_title", "requirements", "proposal", "human_score"])
        for i, it in enumerate(items):
            j = allj[it["job"]]
            w.writerow([f"P{i:02d}", j["title"], "; ".join(j["required_skills"]), it["text"], ""])
    with open(ROOT / "evals/datasets/judge_calibration_key.csv", "w", newline="") as f:  # source labels kept OUT of the labelling sheet
        w = csv.writer(f); w.writerow(["item_id", "source", "job"])
        for i, it in enumerate(items):
            w.writerow([f"P{i:02d}", it["src"], it["job"]])
    print("wrote", SHEET, "-> fill human_score (1-5) yourself")


def read_sheet():
    return list(csv.DictReader(open(SHEET)))


def judge_sheet():
    rows = read_sheet()
    import time
    scores = {}
    for r in rows:
        for attempt in range(4):  # free-tier rate limits return no score: retry with a pause
            scores[r["item_id"]] = judge_one(r["job_title"], r["requirements"], r["proposal"])
            if scores[r["item_id"]]:
                break
            time.sleep(15)
    write("judge_scores.json", scores)
    print(scores)


def cohen_kappa(a, b, labels, weights=None):
    n = len(a)
    idx = {l: i for i, l in enumerate(labels)}
    k = len(labels)
    obs = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[idx[x]][idx[y]] += 1
    ra = [sum(r) for r in obs]
    cb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = lambda i, j: 0 if i == j else ((i - j) ** 2 / (k - 1) ** 2 if weights == "quadratic" else 1)  # noqa: E731
    do = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k)) / n
    de = sum(w(i, j) * ra[i] * cb[j] for i in range(k) for j in range(k)) / n ** 2
    return 1 - do / de if de else 1.0


def kappa():
    rows = read_sheet()
    js = json.loads((RESULTS / "judge_scores.json").read_text())
    pairs = [(int(r["human_score"]), js[r["item_id"]], r) for r in rows if r["human_score"].strip() and js.get(r["item_id"])]
    if len(pairs) < 30:
        print(f"only {len(pairs)}/30 human labels present; label all 30 first"); return
    h, j = [p[0] for p in pairs], [p[1] for p in pairs]
    out = {"n": len(pairs), "kappa_binary_good_ge4": round(cohen_kappa([x >= 4 for x in h], [x >= 4 for x in j], [False, True]), 3),
           "kappa_quadratic_1to5": round(cohen_kappa(h, j, [1, 2, 3, 4, 5], "quadratic"), 3),
           "exact_agreement": round(sum(a == b for a, b in zip(h, j)) / len(h), 3),
           "largest_disagreements": [{"item": p[2]["item_id"], "human": p[0], "judge": p[1], "text": p[2]["proposal"][:300]} for p in sorted(pairs, key=lambda p: -abs(p[0] - p[1]))[:4]]}
    write("judge_calibration.json", out); print(out)


def score_file(path):
    d = json.loads(open(path).read())
    allj = {j["job_id"]: j for p in ("ml", "web", "data") for j in dev(p)}
    sc = [judge_one(allj[r["job"]]["title"], "; ".join(allj[r["job"]]["required_skills"]), r["text"]) for r in d["jobs"] if r.get("text")]
    sc = [s for s in sc if s]
    d["summary"]["judge_score_mean"] = mean(sc); d["summary"]["judge_n"] = len(sc)
    open(path, "w").write(json.dumps(d, indent=1, default=str)); print(path, mean(sc), len(sc))


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"make-sheet": make_sheet, "judge": judge_sheet, "kappa": kappa}.get(cmd, lambda: score_file(sys.argv[2]))()
