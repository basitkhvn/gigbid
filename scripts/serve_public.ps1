# Serve GigBid from this laptop and keep it alive behind a public tunnel (self-healing).
# Usage (PowerShell, repo root):  powershell -ExecutionPolicy Bypass -File scripts\serve_public.ps1
# Tunnel: if .env has NGROK_AUTHTOKEN and NGROK_DOMAIN -> ngrok with that FIXED domain (URL survives restarts).
#         otherwise -> Cloudflare quick tunnel (random URL, changes on every tunnel restart).
# Reads keys from .env (never printed). Needs: .venv, apps/web/out (static UI build), cloudflared or ngrok on PATH.
# Runs forever: every 20 s it checks the API and the tunnel and restarts whichever died. Log: .logs\supervisor.log
$ErrorActionPreference = 'Continue'
$port = if ($env:GIGBID_PORT) { $env:GIGBID_PORT } else { 8001 }
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { Set-Item -Path "env:$($Matches[1])" -Value $Matches[2].Trim('"') } }
$env:PYTHONPATH = '.'; $env:MODEL_PROFILE = 'groq'; $env:GIGSIM_INPROCESS = '1'
$env:MARKETPLACE_RATE_PER_MIN = '600'; $env:GIGSIM_RATE_LIMIT = '600'; $env:GIGSIM_CONNECTS = '100000'   # demo: many clicks/pollers must not trip the simulator's request limits
$env:WEB_DIST = "$root\apps\web\out"; $env:GIGBID_STATE_DIR = "$root\.state"
if (-not $env:CORS_ORIGINS) { $env:CORS_ORIGINS = '*' }          # bearer-token auth (no cookies)
if (-not $env:APP_SECRET_KEY) { $env:APP_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N') }
New-Item -ItemType Directory -Force $env:GIGBID_STATE_DIR, "$root\.logs" | Out-Null
$log = "$root\.logs\supervisor.log"
function Log($m) { "$(Get-Date -f s) $m" | Add-Content $log }
powercfg /change standby-timeout-ac 0 | Out-Null      # no sleep while plugged in
powercfg /change hibernate-timeout-ac 0 | Out-Null
$fixed = [bool]($env:NGROK_AUTHTOKEN -and $env:NGROK_DOMAIN)
if ($fixed) { & ngrok config add-authtoken $env:NGROK_AUTHTOKEN 2>&1 | Out-Null }

function Api-Up { try { (Invoke-WebRequest "http://127.0.0.1:$port/health" -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200 } catch { $false } }
function Stop-Port($p) { Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }
function Start-Api {
  Stop-Port $port
  Start-Process -FilePath "$root\.venv\Scripts\python.exe" -ArgumentList '-m','uvicorn','apps.api.main:app','--host','127.0.0.1','--port',$port -WindowStyle Hidden -RedirectStandardOutput "$root\.logs\api.out" -RedirectStandardError "$root\.logs\api.err"
  for ($i = 0; $i -lt 60; $i++) { Start-Sleep 2; if (Api-Up) { Log "api up on $port"; return } }
  Log "api did not come up (see .logs\api.err)"
}
function Tunnel-Proc { Get-Process -Name cloudflared, ngrok -ErrorAction SilentlyContinue }
function Start-Tunnel {
  Get-Process -Name cloudflared, ngrok -ErrorAction SilentlyContinue | Stop-Process -Force
  Remove-Item "$root\.logs\tunnel.err", "$root\.logs\tunnel.out" -ErrorAction SilentlyContinue
  if ($fixed) {
    Start-Process -FilePath ngrok -ArgumentList 'http',"$port","--domain=$($env:NGROK_DOMAIN)" -WindowStyle Hidden -RedirectStandardOutput "$root\.logs\tunnel.out" -RedirectStandardError "$root\.logs\tunnel.err"
    Set-Content "$root\.logs\public_url.txt" "https://$($env:NGROK_DOMAIN)"; Log "ngrok fixed url https://$($env:NGROK_DOMAIN)"
  } else {
    Start-Process -FilePath cloudflared -ArgumentList 'tunnel','--url',"http://127.0.0.1:$port",'--no-autoupdate' -WindowStyle Hidden -RedirectStandardError "$root\.logs\tunnel.err" -RedirectStandardOutput "$root\.logs\tunnel.out"
    for ($i = 0; $i -lt 40; $i++) {
      Start-Sleep 2
      $m = Select-String -Path "$root\.logs\tunnel.err" -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($m) { Set-Content "$root\.logs\public_url.txt" $m.Matches[0].Value; Log "quick tunnel url $($m.Matches[0].Value) (CHANGES on restart)"; return }
    }
    Log "tunnel url not found (see .logs\tunnel.err)"
  }
}

Log "supervisor start (port $port, fixed-domain=$fixed)"
Start-Api
Start-Tunnel
if (Test-Path "$root\.logs\public_url.txt") { "PUBLIC URL: " + (Get-Content "$root\.logs\public_url.txt") }
while ($true) {
  Start-Sleep 20
  if (-not (Api-Up)) { Log "api down -> restarting"; Start-Api }
  if (-not (Tunnel-Proc)) { Log "tunnel down -> restarting"; Start-Tunnel }
}
