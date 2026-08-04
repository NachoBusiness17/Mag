# Bootstrap an isolated test environment (mirrors docs/GITHUB_PUBLISH.md fresh clone).
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/bootstrap_test_env.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/bootstrap_test_env.ps1 -Launch
param(
    [switch]$Launch,
    [int]$Port = 8770
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$TestRoot = Join-Path (Split-Path -Parent $Root) 'mag_test_env'

Write-Host "== Mag test environment bootstrap =="
Write-Host "Source repo: $Root"
Write-Host "Test worktree: $TestRoot"

if (-not (Test-Path $TestRoot)) {
    Push-Location $Root
    git worktree add $TestRoot -b "env-test-$(Get-Date -Format 'yyyyMMdd')" HEAD
    Pop-Location
}

Set-Location $TestRoot

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host 'Created .env from .env.example (fill API keys for full provider smoke).'
}

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    if (Get-Command py -ErrorAction SilentlyContinue) { py -3.12 -m venv .venv }
    else { python -m venv .venv }
}

$Py = Join-Path $TestRoot '.venv\Scripts\python.exe'
$Pip = Join-Path $TestRoot '.venv\Scripts\pip.exe'
& $Pip install -r (Join-Path $TestRoot 'requirements.txt')

Write-Host "`n== doctor =="
& $Py main.py doctor
$doctorExit = $LASTEXITCODE

Write-Host "`n== pytest =="
& $Py -m pytest tests/ -q --ignore=tests/test_supervision_soak.py
$pytestExit = $LASTEXITCODE

if ($Launch) {
    Write-Host "`n== lab on port $Port (verbatim main.py lab, non-default port to avoid prod clash) =="
    Start-Process -WindowStyle Minimized -FilePath $Py -ArgumentList @('main.py', 'lab', '--port', "$Port")
    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/v1/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { break }
        } catch {}
    } while ((Get-Date) -lt $deadline)
    Write-Host "Dashboard: http://127.0.0.1:$Port/"
    curl.exe -s "http://127.0.0.1:$Port/api/v1/operator-inbox" | Write-Host
    curl.exe -s "http://127.0.0.1:$Port/api/v1/seats" | Write-Host
}

if ($pytestExit -ne 0) { exit $pytestExit }
if ($doctorExit -ne 0 -and -not $Launch) { Write-Host 'doctor degraded (expected on fresh clone without lab running)' }
Write-Host "`nBootstrap complete."
