# Serve GigBid from this laptop and expose it through a free Cloudflare quick tunnel.
# Usage (PowerShell, repo root):  powershell -ExecutionPolicy Bypass -File scripts\serve_public.ps1
# Reads keys from .env (never printed). Needs: .venv, apps/web/out (STATIC_EXPORT build), cloudflared on PATH.
$ErrorActionPreference = 'Stop'
$port = if ($env:GIGBID_PORT) { $env:GIGBID_PORT } else { 8001 }
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { Set-Item -Path "env:$($Matches[1])" -Value $Matches[2].Trim('"') } }
$env:PYTHONPATH = '.'; $env:MODEL_PROFILE = 'groq'; $env:GIGSIM_INPROCESS = '1'
$env:WEB_DIST = "$root\apps\web\out"; $env:GIGBID_STATE_DIR = "$root\.state"
if (-not $env:CORS_ORIGINS) { $env:CORS_ORIGINS = '*' }          # bearer-token auth (no cookies): wildcard is safe enough for a demo
if (-not $env:APP_SECRET_KEY) { $env:APP_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N') }
New-Item -ItemType Directory -Force $env:GIGBID_STATE_DIR, "$root\.logs" | Out-Null
# keep the laptop awake while plugged in (display may still turn off)
powercfg /change standby-timeout-ac 0 | Out-Null
Start-Process -FilePath "$root\.venv\Scripts\python.exe" -ArgumentList '-m','uvicorn','apps.api.main:app','--host','127.0.0.1','--port',$port -WindowStyle Hidden -RedirectStandardOutput "$root\.logs\api.out" -RedirectStandardError "$root\.logs\api.err"
for ($i = 0; $i -lt 60; $i++) { try { if ((Invoke-WebRequest http://127.0.0.1:$port/health -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { break } } catch { Start-Sleep 2 } }
Start-Process -FilePath cloudflared -ArgumentList 'tunnel','--url',"http://127.0.0.1:$port",'--no-autoupdate' -WindowStyle Hidden -RedirectStandardError "$root\.logs\tunnel.err" -RedirectStandardOutput "$root\.logs\tunnel.out"
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep 2
  $m = Select-String -Path "$root\.logs\tunnel.err" -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($m) { $url = $m.Matches[0].Value; break }
}
if ($url) { Set-Content "$root\.logs\public_url.txt" $url; "PUBLIC URL: $url" } else { "Tunnel URL not found; see .logs\tunnel.err" }

