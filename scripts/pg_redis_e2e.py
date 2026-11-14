"""E2E against the Postgres + Redis stack (API :8002 + Arq worker): sign in, queue a bid run, wait for the worker, approve, verify."""
import json
import os
import sys
import time
import urllib.request

BASE = os.environ.get("E2E_BASE", "http://127.0.0.1:8002")
for line in open(".env", encoding="utf-8"):
    if line.startswith("REVIEWER_PASSWORD="):
        PW = line.split("=", 1)[1].strip().strip('"')

def call(path, body=None, token=None, method=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, method=method or ("POST" if body is not None else "GET"),
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    return json.load(urllib.request.urlopen(req, timeout=60))

tok = call("/auth/login", {"email": "reviewer@gigbid.demo", "password": PW})
tok = tok.get("access_token") or tok.get("token")
jobs = call("/jobs?limit=20", token=tok)
jobs = jobs.get("jobs", jobs) if isinstance(jobs, dict) else jobs
cand = next((j for j in jobs if (j.get("triage") or j).get("action", "bid") == "bid"), jobs[0])
jid = cand.get("job_id")
print("job", jid)
rid = call(f"/jobs/{jid}/draft", {}, tok)["run_id"]
print("run", rid)
t0, seen = time.time(), set()
while time.time() - t0 < 240:
    r = call(f"/runs/{rid}", token=tok)
    st = (r.get("run") or r).get("status")
    if st not in seen: print(f"{time.time()-t0:5.1f}s status={st}"); seen.add(st)
    if st in ("awaiting_approval", "needs_attention", "done", "skipped"): break
    time.sleep(2)
if st == "awaiting_approval":
    print("approve ->", call(f"/approvals/{rid}", {"action": "approve"}, tok))
    for _ in range(60):
        time.sleep(2)
        st = (call(f"/runs/{rid}", token=tok).get("run") or {}).get("status")
        if st not in ("running",): break
    print("final status", st)
sys.exit(0 if st in ("submitted", "done") else 1)
