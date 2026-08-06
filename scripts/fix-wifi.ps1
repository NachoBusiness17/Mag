# Fix WLAN config: services stuck Manual+Stopped, phantom USB adapter
# Run: double-click scripts\fix-wifi.cmd  OR  Admin PowerShell: .\scripts\fix-wifi.ps1
$ErrorActionPreference = 'Continue'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator (use fix-wifi.cmd for UAC prompt)" -ForegroundColor Red
    exit 1
}

Write-Host "=== Wi-Fi config fix ===" -ForegroundColor Cyan

# 1. Services: Manual (3) -> Automatic (2), then start chain
$services = @('nativewifip', 'Ndisuio', 'Netman', 'WlanSvc')
foreach ($s in $services) {
    sc.exe config $s start= auto | Out-Null
    Write-Host "config $s start= auto"
}

foreach ($s in @('nativewifip', 'Ndisuio', 'Netman', 'WlanSvc')) {
    try {
        Start-Service $s -ErrorAction Stop
        Write-Host "started $s" -ForegroundColor Green
    } catch {
        Write-Host "start $s failed: $_" -ForegroundColor Yellow
    }
}

# 2. Registry belt-and-suspenders (Start=2 = Automatic)
$regPaths = @(
    'HKLM:\SYSTEM\CurrentControlSet\Services\WlanSvc',
    'HKLM:\SYSTEM\CurrentControlSet\Services\nativewifip',
    'HKLM:\SYSTEM\CurrentControlSet\Services\Ndisuio',
    'HKLM:\SYSTEM\CurrentControlSet\Services\Netman'
)
foreach ($p in $regPaths) {
    if (Test-Path $p) {
        Set-ItemProperty -Path $p -Name Start -Value 2 -Type DWord -Force
        Write-Host "registry $p Start=2"
    }
}

# 3. Remove phantom TP-Link USB (CM_PROB_PHANTOM)
$phantom = Get-PnpDevice -FriendlyName 'TP-Link Wireless USB Adapter' -ErrorAction SilentlyContinue |
    Where-Object { $_.Status -eq 'Unknown' }
if ($phantom) {
    try {
        pnputil /remove-device $phantom.InstanceId 2>&1 | Out-Null
        Write-Host "removed phantom TP-Link adapter" -ForegroundColor Green
    } catch {
        Write-Host "phantom remove skipped: $_" -ForegroundColor Yellow
    }
}

# 4. Bounce Wi-Fi interface
netsh interface set interface "Wi-Fi" disable 2>&1 | Out-Null
Start-Sleep -Seconds 2
netsh interface set interface "Wi-Fi" enable 2>&1 | Out-Null
Write-Host "Wi-Fi interface toggled"

# 5. Report
Write-Host "`n=== After ===" -ForegroundColor Cyan
Get-Service WlanSvc, nativewifip, Ndisuio | Format-Table Name, Status, StartType
netsh wlan show interfaces 2>&1
Write-Host "`nDone. If WlanSvc still stopped, update Intel Wi-Fi driver (yours is 2021-03-03)." -ForegroundColor Cyan
