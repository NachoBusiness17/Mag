# Container-first install — Mag runs in Docker, not as a host desktop pet.
# Agent subprocesses (backend tools, shell, python sandbox) stay in the cage.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\install.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -WithOllama
#   powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -Shortcuts

param(
    [switch]$WithOllama,
    [switch]$Shortcuts,
    [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== Mag install (container boundary) ==" -ForegroundColor Cyan
Write-Host "Mag runs inside Docker — not as raw host subprocesses."
Write-Host "See docs/CONTAINER.md for why this matters.`n"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker Desktop is required." -ForegroundColor Red
    Write-Host "  https://docs.docker.com/desktop/setup/install/windows-install/"
    exit 1
}

docker compose version | Out-Null

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host "Created .env from .env.example — add API keys before remote chat."
}

@('memory/biography', 'memory/briefs', 'watch', 'logs', 'state', 'queue/handoff') | ForEach-Object {
    $p = Join-Path $Root $_
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

$composeArgs = @('compose', 'up', '-d', '--build')
if ($WithOllama) {
    $composeArgs = @('compose', '--profile', 'ollama', 'up', '-d', '--build')
    Write-Host "Including Ollama sidecar (profile: ollama)."
}

Write-Host "`nBuilding and starting container..."
& docker @composeArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Waiting for dashboard health..."
$deadline = (Get-Date).AddSeconds(120)
do {
    Start-Sleep -Seconds 2
    try {
        docker compose exec -T mag python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/v1/health', timeout=2)" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { break }
    } catch {}
} while ((Get-Date) -lt $deadline)

Write-Host "`n== doctor (inside container) =="
docker compose exec -T mag python main.py doctor

if ($Shortcuts) {
    Write-Host "`n== desktop shortcuts (container launchers) =="
    & (Join-Path $Root 'scripts\install_desktop_shortcuts.ps1')
}

Write-Host "`n== done =="
Write-Host "  Dashboard: http://127.0.0.1:8765/"
Write-Host "  CLI in cage:  scripts\mag_exec.ps1 doctor"
Write-Host "  Stop:         stop_mag_container.cmd"
Write-Host "  Logs:         docker compose logs -f mag"

if (-not $NoLaunch) {
    Start-Process 'http://127.0.0.1:8765/'
}
