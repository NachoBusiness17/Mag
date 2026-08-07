# Mag home — one script. Keys in .env, lab up, steering ready.
#   powershell -ExecutionPolicy Bypass -File scripts\go.ps1
param(
    [switch]$Lan,
    [switch]$NoLab
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Host "venv missing — running ensure_venv.ps1 ..."
    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "ensure_venv.ps1")
}

& powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "ensure_local_env.ps1")

# Load .env into this shell (for MAG_REMOTE_TOKEN / keys)
$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim().Trim('"').Trim("'")
            if ($k -and $v) { Set-Item -Path "env:$k" -Value $v }
        }
    }
}

if (-not $env:MAG_REMOTE_TOKEN) {
    $tok = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    Write-Host ""
    Write-Host "MAG_REMOTE_TOKEN was empty — generated one. Add to .env:"
    Write-Host "  MAG_REMOTE_TOKEN=$tok"
    Write-Host "  (same value in Cursor Cloud secrets + MAG_PUBLIC_URL after LAN start)"
    Write-Host ""
    $env:MAG_REMOTE_TOKEN = $tok
}

Write-Host "=== Mag go ===" -ForegroundColor Cyan
& $Py main.py doctor 2>&1 | Select-Object -Last 15
Write-Host ""
& $Py main.py cloud-steering-verify 2>&1

if ($NoLab) { exit 0 }

if ($Lan) {
    Write-Host ""
    Write-Host "Starting LAN dashboard (0.0.0.0:8765) ..." -ForegroundColor Green
    $env:MAG_BIND_HOST = "0.0.0.0"
    & cmd /c (Join-Path $Root "launch_dashboard_lan.cmd")
} else {
    Write-Host ""
    Write-Host "Starting mag.cmd lab (loopback) ..." -ForegroundColor Green
    Write-Host "  For tablet/cloud: re-run with -Lan" -ForegroundColor DarkGray
    & cmd /c (Join-Path $Root "mag.cmd") lab
}
