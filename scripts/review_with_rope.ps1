# review_with_rope.ps1 — Mag pack preamble + trail shell around Grok review-changes
# Law: docs/ref/COORDINATION_ELIAS_ROPE.md
# Usage (from Mag root):
#   .\scripts\review_with_rope.ps1 -Target "origin/main...HEAD"
# Then paste the printed /workflow line into Grok TUI (fullscreen).

param(
    [Parameter(Mandatory = $true)]
    [string]$Target,
    [string]$Seat = "grok_tui"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "Missing $py — use Mag venv, not bare PATH python"
}

$goal = "review-changes target=$Target"
$git = ""
try {
    $git = (git -C $Root rev-parse --short=12 HEAD 2>$null)
} catch { }

if ($git) {
    & $py main.py trail start $goal --seat $Seat --proactivity narrow --force --git-sha $git
} else {
    & $py main.py trail start $goal --seat $Seat --proactivity narrow --force
}
& $py main.py context-pack --agent --goal $goal | Out-Null

$preamble = Join-Path $Root "memory\agent_preamble_latest.md"
$preambleUnix = $preamble -replace '\\', '/'
$baseJson = & $py main.py trail base | Out-String
$baseId = ""
try {
    $baseObj = $baseJson | ConvertFrom-Json
    $baseId = $baseObj.base.base_id
} catch { }

Write-Host ""
Write-Host "=== Elias rope ready (base + drift) ===" -ForegroundColor Cyan
Write-Host "Preamble: $preamble"
Write-Host "base_id:  $baseId"
Write-Host "Trail:    active (mag.cmd trail status | trail drifts)"
Write-Host ""
Write-Host "In Grok TUI run:" -ForegroundColor Yellow
$payload = @{ target = $Target; preamble_path = $preambleUnix }
if ($baseId) { $payload.base_id = $baseId }
$json = $payload | ConvertTo-Json -Compress
Write-Host "/workflow review-changes $json"
Write-Host ""
Write-Host "After workflow, FILE drift then close:" -ForegroundColor Yellow
Write-Host "  mag.cmd trail append `"finding`" --label review:security --locus path --drift-kind finding --evidence `"file:line`" --base-id $baseId"
Write-Host "  mag.cmd trail drifts"
Write-Host "  mag.cmd trail close"
Write-Host ""
Write-Host "Does not green republic R0. Instrument body only."
