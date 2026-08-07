# Install MAG full-stack boot into Windows Startup (login).
# Run once:  powershell -ExecutionPolicy Bypass -File scripts\install_mag_startup.ps1
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Boot = Join-Path $Root "boot_mag.cmd"
if (-not (Test-Path $Boot)) {
  Write-Error "Missing boot_mag.cmd at $Boot"
  exit 1
}
$Startup = [Environment]::GetFolderPath("Startup")
$LnkPath = Join-Path $Startup "MAG Start.lnk"
$W = New-Object -ComObject WScript.Shell
$L = $W.CreateShortcut($LnkPath)
$L.TargetPath = $Boot
$L.WorkingDirectory = $Root
$L.WindowStyle = 7  # minimized
$L.Description = "MAG full stack + Direct Mag UI"
$L.Save()
Write-Host "Installed: $LnkPath"
Write-Host "  -> $Boot"
Write-Host "Login will run power start and open http://127.0.0.1:8765/?tab=chat"
Write-Host "Kill: mag_kill.cmd   Status: mag.cmd power status"
