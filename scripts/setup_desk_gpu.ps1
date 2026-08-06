# Desk GPU setup — RX 5600 XT (6GB) + Ollama DirectML
# Run once: powershell -ExecutionPolicy Bypass -File scripts\setup_desk_gpu.ps1
#
# Problem: gemma4:latest @ OLLAMA_CONTEXT_LENGTH=65536 uses ~27% GPU / 73% CPU
# Fix: gemma4-desk with num_ctx 8192 — fits mostly on GPU, desk doesn't need 64k

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

Write-Host "=== Desk GPU setup (AMD RX 5600 XT) ==="

# 1) Desk model — 8k context (Hermes keeps global 65536; desk Modelfile overrides per model)
$tag = "gemma4-desk"
$mf = @"
FROM gemma4:latest
PARAMETER num_ctx 8192
PARAMETER temperature 0.35
PARAMETER top_p 0.9
"@
$mfPath = Join-Path $env:TEMP "Modelfile.gemma4-desk"
Set-Content -Path $mfPath -Value $mf -Encoding utf8
Write-Host "Creating ollama model $tag (8192 ctx for GPU fit)..."
ollama create $tag -f $mfPath

# 2) Patch lanes.yaml desk_orchestrator if still on gemma4:latest
$lanesPath = Join-Path $Root "configs\lanes.yaml"
$lanes = Get-Content $lanesPath -Raw -Encoding utf8
if ($lanes -match "desk_orchestrator:\s*gemma4:latest") {
    $lanes = $lanes -replace "desk_orchestrator:\s*gemma4:latest", "desk_orchestrator: gemma4-desk"
    Set-Content -Path $lanesPath -Value $lanes -Encoding utf8 -NoNewline
    Write-Host "Updated configs/lanes.yaml desk_orchestrator -> gemma4-desk"
} else {
    Write-Host "lanes.yaml desk_orchestrator already custom — edit manually if needed"
}

# 3) Warm + verify GPU split
Write-Host "Warming $tag..."
ollama run $tag "ok" --verbose 2>&1 | Select-String -Pattern "gpu|processor|vram" -CaseSensitive:$false
Start-Sleep 1
$ps = (Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/ps" -TimeoutSec 10).models |
    Where-Object { $_.name -eq "${tag}:latest" -or $_.name -eq $tag } | Select-Object -First 1
if ($ps) {
    $gpuPct = [math]::Round(100 * $ps.size_vram / $ps.size, 0)
    Write-Host "Loaded: $($ps.name) · VRAM $([math]::Round($ps.size_vram/1GB,2))GB / $([math]::Round($ps.size/1GB,2))GB · GPU ~${gpuPct}%"
} else {
    Write-Host "Warm complete — check: ollama ps"
}

Write-Host ""
Write-Host "=== Unsloth Studio (optional GPU agent) ==="
$unsloth = Join-Path $env:USERPROFILE ".unsloth\studio\bin\unsloth.exe"
if (Test-Path $unsloth) {
    Write-Host "  Chat:    & '$unsloth' chat --model <path-or-hf-id>"
    Write-Host "  Agent:   & '$unsloth' start  (Hermes/Codex-style against local model)"
    Write-Host "  Export:  fine-tune in Studio -> export GGUF -> ollama create desk-custom -f Modelfile"
} else {
    Write-Host "  Unsloth Studio not found at $unsloth"
}

Write-Host ""
Write-Host "=== next ==="
Write-Host "  python main.py desk reload"
Write-Host "  Ctrl+Shift+R browser"
Write-Host "  ollama ps  (expect gemma4-desk mostly GPU, not 73/27 CPU/GPU)"
