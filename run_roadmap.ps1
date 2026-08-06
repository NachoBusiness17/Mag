$ErrorActionPreference = "Stop"
$MagRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $MagRoot
$Python = Join-Path $MagRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Missing Mag virtual environment. Run scripts\ensure_venv.ps1 first."
}
& $Python (Join-Path $MagRoot "main.py") roadmap-run run @args
exit $LASTEXITCODE
