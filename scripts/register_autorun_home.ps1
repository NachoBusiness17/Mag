# Enable home autorun: drainer preference + optional scheduled autopilot pass.
#   powershell -ExecutionPolicy Bypass -File scripts\register_autorun_home.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\register_autorun_home.ps1 -ScheduleHourly
param([switch]$ScheduleHourly)

$ErrorActionPreference = "Continue"
$Root = Split-Path $PSScriptRoot -Parent
$Py = Join-Path $Root ".venv\Scripts\python.exe"
Set-Location $Root

if (-not (Test-Path $Py)) {
    Write-Error "Missing $Py — run scripts\ensure_venv.ps1"
    exit 1
}

Write-Host "Enabling drainer preference (supervisor picks up within ~5s when lab is running)..."
& $Py -c @"
from mag.preferences import set_drainer, drainer_status
set_drainer(True)
import json
print(json.dumps(drainer_status(), indent=2))
"@

Write-Host ""
Write-Host "Recommended env for this shell / Task Scheduler:"
Write-Host "  set MAG_DRAINER=1"
Write-Host "  mag.cmd lab"
Write-Host ""
Write-Host "Governor burst (manual):  mag.cmd governor --run 3"
Write-Host "Autopilot API:            python watch/cursor_bridge.py autopilot --drain"

if (-not $ScheduleHourly) {
    Write-Host ""
    Write-Host "Optional hourly autopilot: re-run with -ScheduleHourly"
    exit 0
}

$Script = Join-Path $PSScriptRoot "autorun_hourly.ps1"
$TaskName = "MagAutorunHourly"
$Tr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$Script`""

schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
schtasks.exe /Create /TN $TaskName /TR $Tr /SC HOURLY /RL LIMITED /F
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN: schtasks create failed (exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}
Write-Host "OK: task '$TaskName' → hourly autopilot (improve + governor)"
Write-Host "Test: schtasks /Run /TN $TaskName"
