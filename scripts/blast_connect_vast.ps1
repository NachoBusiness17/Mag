# Windows side: after Vast is up and ollama bootstrap ran.
# Usage:
#   .\scripts\blast_connect_vast.ps1 -HostIp 1.2.3.4 -Port 22 -User root
# Keeps SSH tunnel in this window; open another terminal for Mag blast.
param(
    [Parameter(Mandatory = $true)][string]$HostIp,
    [int]$Port = 22,
    [string]$User = "root",
    [int]$LocalPort = 11434
)

$ErrorActionPreference = "Stop"
Write-Host "Tunnel: localhost:$LocalPort -> ${User}@${HostIp}:$Port -> 127.0.0.1:11434"
Write-Host "Leave this window open. In Mag root then:"
Write-Host "  `$env:OLLAMA_HOST = 'http://127.0.0.1:$LocalPort'"
Write-Host "  .\.venv\Scripts\python.exe main.py blast --status"
Write-Host "  .\.venv\Scripts\python.exe main.py lab   # dash :8765 → BST"
Write-Host "  .\.venv\Scripts\python.exe main.py blast --run --bg"
Write-Host ""

ssh -N -L "${LocalPort}:127.0.0.1:11434" -p $Port "${User}@${HostIp}"
