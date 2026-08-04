# Create or open Mag .env for local API keys (never commit .env).
#   powershell -ExecutionPolicy Bypass -File scripts\ensure_local_env.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\ensure_local_env.ps1 -Open
param([switch]$Open)

$Root = Split-Path $PSScriptRoot -Parent
$Example = Join-Path $Root ".env.example"
$EnvFile = Join-Path $Root ".env"

if (-not (Test-Path $Example)) {
    Write-Error "Missing $Example"
    exit 1
}

if (-not (Test-Path $EnvFile)) {
    Copy-Item $Example $EnvFile
    Write-Host "Created $EnvFile from .env.example"
} else {
    Write-Host "Using existing $EnvFile"
}

Write-Host ""
Write-Host "Paste DEEPSEEK_API_KEY=sk-... into .env (local only — not GitHub)."
Write-Host "Then: mag.cmd doctor && mag.cmd agent --provider deepseek -q `"say ok`""
Write-Host ""

if ($Open) {
    notepad $EnvFile
}

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $Py) {
    & $Py -c @"
from models.env_load import load_dotenv
from pathlib import Path
import os
load_dotenv(Path(r'$EnvFile'), override=True)
for k in ('DEEPSEEK_API_KEY','DEEPSEEK_OVERMIND_API_KEY','MAG_REMOTE_TOKEN'):
    v = os.environ.get(k,'').strip()
    print(f'{k}:', 'configured' if v else 'empty')
"@
}
