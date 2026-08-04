# FILE a Cursor cloud run back to home Mag (handoff → queue/working + optional Verkle).
#   powershell -ExecutionPolicy Bypass -File scripts\file_cloud_run.ps1 `
#     -Seat cursor-cloud-bc123 -Goal "wire X" -NextMove "merge PR and seat-file"
#
# Requires MAG_PUBLIC_URL + MAG_REMOTE_TOKEN (or local mag.cmd lab on loopback).
param(
    [Parameter(Mandatory = $true)][string]$Seat,
    [string]$Goal = "",
    [string]$Turned = "",
    [string]$OpenLoops = "",
    [string]$NextMove = "",
    [string]$PrUrl = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Py)) {
    Write-Error "Missing venv python at $Py"
    exit 1
}

$turned = if ($Turned) { $Turned } else { "cloud run $Seat" }
$loops = if ($OpenLoops) { $OpenLoops } else { "see PR / chat" }
$next = if ($NextMove) { $NextMove } elseif ($Goal) { $Goal } else { "git pull on home; mag.cmd seat-file --seat $Seat --source cloud" }

$block = @(
    "FILE for Mag:",
    "- turned: $turned",
    "- open loops: $loops",
    "- next move: $next"
)
if ($PrUrl) { $block += "- pr: $PrUrl" }
if ($Goal -and $Goal -ne $next) { $block += "- goal: $Goal" }
$text = ($block -join "`n")

$args = @(
    "watch/cursor_bridge.py", "handoff", $text,
    "--source", $Seat,
    "--device", "file-cloud-run",
    "--kind", "auto"
)

Write-Host "POST handoff/file via cursor_bridge..."
& $Py @args
exit $LASTEXITCODE
