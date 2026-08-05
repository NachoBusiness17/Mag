# Register Windows Task Scheduler job for Mag improve --once (daily 08:00).
# PREFERRED: Mag orchestrator + drainer (Status tab → daily improve ON, drainer ON).
# This script remains a fallback when Mag is not running at 08:00 ET.
#   powershell -ExecutionPolicy Bypass -File scripts\register_improve_task.ps1
$ErrorActionPreference = "Continue"
$Root = Split-Path $PSScriptRoot -Parent
$Script = Join-Path $PSScriptRoot "improve_daily.ps1"
$TaskName = "MagImproveDaily"

if (-not (Test-Path $Script)) {
    Write-Error "Missing $Script"
    exit 1
}

# Delete if exists (ignore missing)
$prev = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
$ErrorActionPreference = $prev

$Tr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$Script`""
& schtasks.exe /Create /TN $TaskName /TR $Tr /SC DAILY /ST 08:00 /RL LIMITED /F
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN: schtasks create failed (exit $LASTEXITCODE)."
    Write-Host "Create manually:"
    Write-Host "  Program: powershell.exe"
    Write-Host "  Args:    -NoProfile -ExecutionPolicy Bypass -File `"$Script`""
    Write-Host "  Start in: $Root"
    Write-Host "  Trigger: Daily 08:00"
    exit $LASTEXITCODE
}

Write-Host "OK: task '$TaskName' → daily 08:00"
Write-Host "    script: $Script"
Write-Host "    log:    $Root\logs\improve_daily.log"
Write-Host "Test now:  schtasks /Run /TN $TaskName"
Write-Host "Or:        powershell -File `"$Script`""
