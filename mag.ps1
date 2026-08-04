# Mag launcher - project .venv only
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Py = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Py)) { Write-Error 'Missing Mag venv. Run scripts\ensure_venv.ps1' }
& $Py (Join-Path $Root 'main.py') @args
exit $LASTEXITCODE