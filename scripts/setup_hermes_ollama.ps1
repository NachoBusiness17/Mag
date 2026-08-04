# Fix Hermes + local Ollama for agent tool use.
# Run once (or after model changes): powershell -File scripts\setup_hermes_ollama.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

Write-Host "=== Hermes Ollama setup ==="

# 1) Force Ollama context (user env — restart Ollama app if already running)
[System.Environment]::SetEnvironmentVariable("OLLAMA_CONTEXT_LENGTH", "65536", "User")
$env:OLLAMA_CONTEXT_LENGTH = "65536"
Write-Host "OLLAMA_CONTEXT_LENGTH=65536 (User env)"

# 2) Agent model: gemma4 with num_ctx + lower temp
$base = "gemma4:latest"
$tag = "gemma4-hermes"
$mf = @"
FROM $base
PARAMETER num_ctx 65536
PARAMETER temperature 0.2
PARAMETER top_p 0.9
"@
$mfPath = Join-Path $env:TEMP "Modelfile.gemma4-hermes"
Set-Content -Path $mfPath -Value $mf -Encoding utf8
Write-Host "Creating ollama model $tag from $base ..."
ollama create $tag -f $mfPath

# 3) Hermes config
hermes config set model.default $tag
hermes config set model.provider custom
hermes config set model.base_url http://127.0.0.1:11434/v1
hermes config set model.context_length 65536

# 4) Stop clarify theater in CLI
try { hermes tools disable clarify 2>$null } catch {}

# 5) .env
$envPath = Join-Path $env:LOCALAPPDATA "hermes\.env"
$lines = @()
if (Test-Path $envPath) { $lines = Get-Content $envPath }
function Ensure-Line([string[]]$L, [string]$Key, [string]$Val) {
    $found = $false
    $out = @()
    foreach ($line in $L) {
        if ($line -match "^\s*$Key\s*=") { $out += "$Key=$Val"; $found = $true }
        else { $out += $line }
    }
    if (-not $found) { $out += "$Key=$Val" }
    return $out
}
$lines = Ensure-Line $lines "OPENAI_API_KEY" "ollama"
$lines = Ensure-Line $lines "HERMES_API_TIMEOUT" "1800"
Set-Content -Path $envPath -Value ($lines -join "`n") -Encoding utf8
Write-Host "Wrote $envPath"

# 6) SOUL with Mag root
$soul = @"
# Mag seat

ROOT = $Root
Always tool from that directory. No path questions.
Read AGENTS.md, memory/improve/field_brief.md, memory/working.md first when doing Mag work.
One job. Use tools. Never roleplay tool calls.
"@
$soulPath = Join-Path $env:LOCALAPPDATA "hermes\SOUL.md"
Set-Content -Path $soulPath -Value $soul -Encoding utf8
Write-Host "SOUL: $soulPath"

# 7) Smoke: force a real file write
$probe = Join-Path $Root "memory\_hermes_probe.txt"
if (Test-Path $probe) { Remove-Item $probe -Force }
Write-Host "Running tool probe (may take 1-3 min)..."
$py = Join-Path $Root ".venv\Scripts\python.exe"
& $py -c @"
from pathlib import Path
from harness.hermes_cli import escalate_via_hermes
root = Path(r'$Root')
probe = root / 'memory' / '_hermes_probe.txt'
res = escalate_via_hermes(
    goal='Write exactly the text HERMES_TOOLS_OK to memory/_hermes_probe.txt using the file or terminal tool. No questions.',
    context='Mag probe. cwd is project root.',
    cwd=root,
    max_turns=12,
    yolo=True,
    expect_path=probe,
    timeout=600,
)
print('ok=', res.get('ok'), 'theater=', res.get('tool_theater'), 'missing=', res.get('expect_missing'))
print('summary=', res.get('summary'))
print('error=', res.get('error'))
print('exists=', probe.is_file())
if probe.is_file():
    print('content=', probe.read_text(encoding='utf-8')[:200])
"@

Write-Host "=== done. Restart Hermes TUI if open. Model: $tag ==="
Write-Host "If probe fails (tool theater): pull a stronger tool model, e.g. ollama pull qwen2.5-coder:14b"
Write-Host "  then: hermes config set model.default qwen2.5-coder:14b"
