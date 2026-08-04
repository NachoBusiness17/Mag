# Install desktop shortcuts — container launchers (not host-native mag_launch).

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

$launchCmd = Join-Path $MagRoot "launch_mag_container.cmd"
$shellCmd = Join-Path $MagRoot "launch_sovereign_shell_container.cmd"
$stopCmd = Join-Path $MagRoot "stop_mag_container.cmd"
$ico = Join-Path $MagRoot "mag_agent.ico"

Write-Host "Installing container-bound shortcuts (agent tools stay in Docker)."

if (Test-Path $launchCmd) {
    New-Shortcut "Mag Office" "cmd.exe" "/c `"$launchCmd`"" $ico "Mag dashboard — container :8765"
}

if (Test-Path $shellCmd) {
    New-Shortcut "Mag Shell" "cmd.exe" "/c `"$shellCmd`"" $ico "Mag sovereign shell — container :8765/shell"
}

if (Test-Path $stopCmd) {
    New-Shortcut "Mag Stop" "cmd.exe" "/c `"$stopCmd`"" $ico "Stop Mag Docker stack"
}

Write-Host "Done. Host does not run mag_launch directly — see docs/CONTAINER.md"
