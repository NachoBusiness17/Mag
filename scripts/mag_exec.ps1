# Run a Mag CLI command inside the container (keeps tools off the host).
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error 'Docker not found. Start with launch_mag_container.cmd first.'
}

if ($Args.Count -eq 0) {
    docker compose exec mag python main.py --help
    exit 0
}

docker compose exec mag python main.py @Args
