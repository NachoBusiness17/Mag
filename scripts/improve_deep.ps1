# Mag improve deep dive — research-pack + local Ollama on field tickets.
# Opt-in. Not registered as a scheduled task by default.
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\improve_deep.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\improve_deep.ps1 -Minutes 60 -MaxTickets 4
param(
    [int]$Minutes = 60,
    [int]$MaxTickets = 4
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
$LogDir = Join-Path $Root "logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$Log = Join-Path $LogDir "improve_deep.log"
$Stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Write-Log([string]$Msg) {
    $line = "[$Stamp] $Msg"
    Add-Content -Path $Log -Value $line -Encoding utf8
    Write-Host $line
}

if (-not (Test-Path $Py)) {
    Write-Log "FAIL: missing venv python at $Py"
    exit 1
}

Write-Log "START improve --deep --minutes $Minutes --max-tickets $MaxTickets cwd=$Root"
try {
    & $Py main.py improve --deep --minutes $Minutes --max-tickets $MaxTickets 2>&1 | Tee-Object -FilePath $Log -Append
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
    Write-Log "END exit=$code report=memory/improve/deep/latest.md"
    exit $code
} catch {
    Write-Log "FAIL: $_"
    exit 1
}
