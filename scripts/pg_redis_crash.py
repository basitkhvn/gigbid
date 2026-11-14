"""Crash-and-resume on Postgres: queue a run, kill the API while it waits for approval, restart it, approve, expect exactly one submission."""
import json
import subprocess
import time
import urllib.request

BASE = "http://127.0.0.1:8002"
for line in open(".env", encoding="utf-8"):
    if line.startswith("REVIEWER_PASSWORD="): PW = line.split("=", 1)[1].strip().strip('"')
def call(path, body=None, token=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    return json.load(urllib.request.urlopen(req, timeout=60))
def login():
    t = call("/auth/login", {"email": "reviewer@gigbid.demo", "password": PW}); return t.get("access_token") or t.get("token")
def wait(rid, tok, want, secs=240):
    t0 = time.time()
    while time.time() - t0 < secs:
        st = (call(f"/runs/{rid}", token=tok).get("run") or {}).get("status")
        if st in want: return st
        time.sleep(2)
    return st
tok = login()
jobs = call("/jobs?limit=20", token=tok); jobs = jobs.get("jobs", jobs)
done = {r["job_id"] for r in call("/runs", token=tok)} if True else set()
jid = next(j["job_id"] for j in jobs if j["job_id"] not in done and (j.get("triage") or j).get("action") == "bid")
rid = call(f"/jobs/{jid}/draft", {}, tok)["run_id"]
rid2 = call(f"/jobs/{jid}/draft", {}, tok)["run_id"]   # double click: must not start a second run
print("job", jid, "| same run id on double enqueue:", rid == rid2)
print("1. reached", wait(rid, tok, ("awaiting_approval", "needs_attention")))
out = subprocess.run(["powershell", "-Command", "Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'apps[.]api[.]serv[e]' } | % { Stop-Process -Id $_.ProcessId -Force; $_.ProcessId }"], capture_output=True, text=True).stdout.split()
print("2. killed API pid(s)", out)
time.sleep(2)
subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "scripts/run_pg_redis.ps1", "-ApiOnly"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
for _ in range(40):
    try: call("/health"); break
    except Exception: time.sleep(2)
tok = login()
print("3. after restart, status still", (call(f"/runs/{rid}", token=tok).get("run") or {}).get("status"))
print("4. approve ->", call(f"/approvals/{rid}", {"action": "approve"}, tok))
print("5. final", wait(rid, tok, ("submitted", "needs_attention", "rejected"), 120))
