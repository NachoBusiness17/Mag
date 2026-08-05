# Install desktop shortcuts — host-native + container

$ErrorActionPreference = "Stop"
$MagRoot = Split-Path -Parent $PSScriptRoot
$Desktop = [Environment]::GetFolderPath("Desktop")

function New-Shortcut($Name, $Target, $Arguments, $Icon, $Desc) {
    $sh = New-Object -ComObject WScript.Shell
    $lnk = Join-Path $Desktop "$Name.lnk"
    $sc = $sh.CreateShortcut($lnk)
    $sc.TargetPath = $Target
    if ($Arguments) { $sc.Arguments = $Arguments }
    $sc.WorkingDirectory = $MagRoot
    if ($Icon -and (Test-Path $Icon)) { $sc.IconLocation = $Icon }
    $sc.Description = $Desc
    $sc.Save()
    Write-Host "Created $lnk"
}

$ico = Join-Path $MagRoot "mag_agent.ico"

Write-Host "Installing Mag desktop shortcuts..."

# Host-native (recommended on home PC)
$onCmd = Join-Path $MagRoot "mag_on.cmd"
$killCmd = Join-Path $MagRoot "mag_kill.cmd"
$desktopCmd = Join-Path $MagRoot "launch_desktop.cmd"
$queueCmd = Join-Path $MagRoot "launch_agent_queue.cmd"

if (Test-Path $onCmd) {
    New-Shortcut "Mag ON" "cmd.exe" "/c `"$onCmd`"" $ico "Turn on Mag stack (dashboard :8765)"
}
if (Test-Path $killCmd) {
    New-Shortcut "Mag KILL" "cmd.exe" "/c `"$killCmd`"" $ico "Kill switch — stop all Mag Python processes"
}
if (Test-Path $desktopCmd) {
    New-Shortcut "Mag Desktop" "cmd.exe" "/c `"$desktopCmd`"" $ico "Turn on + register Cursor seat"
}
if (Test-Path $queueCmd) {
    New-Shortcut "Mag Queue Agent" "cmd.exe" "/c `"$queueCmd`" `"Paste goal here`"" $ico "Queue one restful agent goal (not REPL)"
}

# Container (optional)
$launchCmd = Join-Path $MagRoot "launch_mag_container.cmd"
$shellCmd = Join-Path $MagRoot "launch_sovereign_shell_container.cmd"
$stopCmd = Join-Path $MagRoot "stop_mag_container.cmd"

if (Test-Path $launchCmd) {
    New-Shortcut "Mag Office (Docker)" "cmd.exe" "/c `"$launchCmd`"" $ico "Mag dashboard — container :8765"
}
if (Test-Path $shellCmd) {
    New-Shortcut "Mag Shell (Docker)" "cmd.exe" "/c `"$shellCmd`"" $ico "Mag sovereign shell — container"
}
if (Test-Path $stopCmd) {
    New-Shortcut "Mag Stop (Docker)" "cmd.exe" "/c `"$stopCmd`"" $ico "Stop Mag Docker stack"
}

Write-Host "Done. Daily: Mag ON → work → Mag KILL"
