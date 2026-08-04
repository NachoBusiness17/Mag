# Hourly autopilot pass when lab/supervisor may be down — queue improve + governor.
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$LogDir = Join-Path $Root "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$Log = Join-Path $LogDir "autorun_hourly.log"
$Stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Write-Log([string]$Msg) {
    $line = "[$Stamp] $Msg"
    Add-Content -Path $Log -Value $line -Encoding utf8
    Write-Host $line
}

if (-not (Test-Path $Py)) {
    Write-Log "FAIL: missing venv"
    exit 1
}

Write-Log "START autopilot"
& $Py main.py autopilot --drain 2>&1 | Tee-Object -FilePath $Log -Append
$code = $LASTEXITCODE
if ($null -eq $code) { $code = 0 }
Write-Log "END exit=$code"
exit $code
