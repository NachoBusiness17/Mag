# Install desktop shortcuts - host-native + container

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

$onCmd = Join-Path $MagRoot "mag_on.cmd"
$killCmd = Join-Path $MagRoot "mag_kill.cmd"
$desktopCmd = Join-Path $MagRoot "launch_desktop.cmd"
$queueCmd = Join-Path $MagRoot "launch_agent_queue.cmd"
$runSprintCmd = Join-Path $MagRoot "launch_run_sprint.cmd"
$agentDeskCmd = Join-Path $MagRoot "launch_agent_desk.cmd"
$agentMachineCmd = Join-Path $MagRoot "launch_agent_machine.cmd"

if (Test-Path $onCmd) {
    New-Shortcut "Mag ON" "cmd.exe" "/c `"$onCmd`"" $ico 'Turn on Mag stack - dashboard port 8765'
}
if (Test-Path $killCmd) {
    New-Shortcut "Mag KILL" "cmd.exe" "/c `"$killCmd`"" $ico 'Kill switch - stop all Mag Python processes'
}
if (Test-Path $desktopCmd) {
    New-Shortcut "Mag Desktop" "cmd.exe" "/c `"$desktopCmd`"" $ico 'Turn on and register Cursor seat'
}
if (Test-Path $queueCmd) {
    New-Shortcut "Mag Queue Agent" "cmd.exe" "/c `"$queueCmd`" `"Paste goal here`"" $ico 'Queue one restful agent goal - not REPL'
}
if (Test-Path $runSprintCmd) {
    New-Shortcut "Mag Run Sprint" "cmd.exe" "/k `"$runSprintCmd`"" $ico 'Run coding-session sprint until closed - prompts for goal'
}
if (Test-Path $agentDeskCmd) {
    New-Shortcut "Mag Agent" "cmd.exe" "/c `"$agentDeskCmd`"" $ico 'Agent desk only - opens Chat tab on port 8765'
}
if (Test-Path $agentMachineCmd) {
    New-Shortcut "Mag Factory Machine" "cmd.exe" "/k `"$agentMachineCmd`"" $ico 'Full machine - branch sprint retro bead behavioral'
}

$launchCmd = Join-Path $MagRoot "launch_mag_container.cmd"
$shellCmd = Join-Path $MagRoot "launch_sovereign_shell_container.cmd"
$stopCmd = Join-Path $MagRoot "stop_mag_container.cmd"

if (Test-Path $launchCmd) {
    New-Shortcut 'Mag Office (Docker)' "cmd.exe" "/c `"$launchCmd`"" $ico 'Mag dashboard - Docker container port 8765'
}
if (Test-Path $shellCmd) {
    New-Shortcut 'Mag Shell (Docker)' "cmd.exe" "/c `"$shellCmd`"" $ico 'Mag sovereign shell - Docker container'
}
if (Test-Path $stopCmd) {
    New-Shortcut 'Mag Stop (Docker)' "cmd.exe" "/c `"$stopCmd`"" $ico 'Stop Mag Docker stack'
}

Write-Host 'Done. Daily: Mag ON, work, Mag KILL'
