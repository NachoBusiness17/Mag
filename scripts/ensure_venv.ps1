# Ensure Mag .venv exists and core deps import. Idempotent.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$VenvPy = Join-Path $Root '.venv\Scripts\python.exe'
$VenvPip = Join-Path $Root '.venv\Scripts\pip.exe'
if (-not (Test-Path $VenvPy)) {
    Write-Host 'Creating .venv...'
    if (Get-Command py -ErrorAction SilentlyContinue) { py -3.12 -m venv .venv } else { python -m venv .venv }
}
Write-Host 'Installing requirements.txt...'
& $VenvPip install -r (Join-Path $Root 'requirements.txt')
& $VenvPy -c "import langgraph, httpx, reportlab; print('OK')"
Write-Host 'Use: mag.cmd doctor   or   .\mag.ps1 doctor'