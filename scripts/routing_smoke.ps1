# Routing smoke — run on home PC after .env keys loaded
#   powershell -ExecutionPolicy Bypass -File scripts\routing_smoke.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
& $Py (Join-Path $Root "scripts\routing_smoke.py")
exit $LASTEXITCODE
