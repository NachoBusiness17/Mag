# Copy Mag Cursor hooks + seat rule into .cursor/ (gitignored locally)

$ErrorActionPreference = "Stop"
$MagRoot = Split-Path -Parent $PSScriptRoot
$CursorDir = Join-Path $MagRoot ".cursor"
$RulesDir = Join-Path $CursorDir "rules"
$SrcHooks = Join-Path $MagRoot "configs\cursor\hooks.json"
$SrcRule = Join-Path $MagRoot "configs\cursor\rules\mag-cursor-seat.mdc"

New-Item -ItemType Directory -Force -Path $CursorDir | Out-Null
New-Item -ItemType Directory -Force -Path $RulesDir | Out-Null

Copy-Item -Force $SrcHooks (Join-Path $CursorDir "hooks.json")
Copy-Item -Force $SrcRule (Join-Path $RulesDir "mag-cursor-seat.mdc")

Write-Host "Installed .cursor/hooks.json and .cursor/rules/mag-cursor-seat.mdc"
Write-Host "Restart Cursor IDE to load hooks."
