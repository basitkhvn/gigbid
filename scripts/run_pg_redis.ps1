# Run GigBid against Postgres + Redis (no Docker): API on :8002 + Arq worker. Services live in WSL Ubuntu:
#   wsl -d Ubuntu -e bash -c "service postgresql start; service redis-server start"
# DB:  create user gigbid password 'gigbid'; createdb -O gigbid gigbid   (see docs/RUNBOOK.md)
param([switch]$ApiOnly)
$ErrorActionPreference = 'Continue'
Set-Location (Split-Path -Parent $PSScriptRoot); $root = (Get-Location).Path
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { Set-Item -Path "env:$($Matches[1])" -Value $Matches[2].Trim('"') } }
$env:PYTHONPATH='.'; $env:MODEL_PROFILE='groq'; $env:GIGSIM_INPROCESS='1'; $env:CORS_ORIGINS='*'; $env:MARKETPLACE_RATE_PER_MIN='600'; $env:GIGSIM_RATE_LIMIT='600'; $env:GIGSIM_CONNECTS='100000'
$env:DATABASE_URL='postgresql://gigbid:gigbid@127.0.0.1:5432/gigbid'; $env:REDIS_URL='redis://127.0.0.1:6379/0'
$env:GIGBID_STATE_DIR="$root\.state_pg"; $env:WEB_DIST="$root\apps\web\out"
New-Item -ItemType Directory -Force $env:GIGBID_STATE_DIR, "$root\.logs" | Out-Null
Start-Process "$root\.venv\Scripts\python.exe" -ArgumentList '-m','apps.api.serve' -WindowStyle Hidden -RedirectStandardOutput "$root\.logs\pg_api.out" -RedirectStandardError "$root\.logs\pg_api.err"
if (-not $ApiOnly) { Start-Process "$root\.venv\Scripts\python.exe" -ArgumentList '-m','worker.run' -WindowStyle Hidden -RedirectStandardOutput "$root\.logs\pg_worker.out" -RedirectStandardError "$root\.logs\pg_worker.err" }
