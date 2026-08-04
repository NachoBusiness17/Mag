# Verify home Mag is ready for Cursor Cloud steering.
#   powershell -ExecutionPolicy Bypass -File scripts\verify_cloud_steering.ps1
$ErrorActionPreference = "Continue"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Host "FAIL: missing venv — run scripts\ensure_venv.ps1"
    exit 1
}

if (-not $env:MAG_REMOTE_TOKEN) {
    $suggest = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    Write-Host ""
    Write-Host "MAG_REMOTE_TOKEN is not set. Suggested (set before LAN launch):"
    Write-Host "  set MAG_REMOTE_TOKEN=$suggest"
    Write-Host ""
}

& $Py main.py cloud-steering-verify --write state/cloud_steering_report.json
exit $LASTEXITCODE
