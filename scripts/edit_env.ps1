# Open Mag .env for editing keys, then print which providers are configured.
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -ErrorAction SilentlyContinue
if (-not $Root) { $Root = "C:\Users\foste\Documents\projects\local_sovereign_agent" }
$envFile = Join-Path $Root ".env"
if (-not (Test-Path $envFile)) {
  Copy-Item (Join-Path $Root ".env.example") $envFile
}
Write-Host "Edit keys in: $envFile"
Write-Host "Save, close editor, then re-run: python main.py providers"
notepad $envFile
cd $Root
.\.venv\Scripts\python.exe main.py providers
