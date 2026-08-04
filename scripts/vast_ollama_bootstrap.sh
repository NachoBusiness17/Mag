#!/usr/bin/env bash
# Run ON the Vast instance after rent (SSH in).
# Installs Ollama, pulls Mag worker models for 48GB class cards.
set -euo pipefail

echo "== Mag Vast Ollama bootstrap =="

if ! command -v curl >/dev/null 2>&1; then
  apt-get update -y && apt-get install -y curl
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
fi

# Listen on all interfaces so SSH tunnel / host port map works
export OLLAMA_HOST=0.0.0.0:11434

# Start server if not up
if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Starting ollama serve..."
  nohup ollama serve >/tmp/ollama-serve.log 2>&1 &
  sleep 3
fi

echo "Pulling models (48GB-friendly stack)..."
# clerk small + strong worker + embed — adjust if VRAM tight
ollama pull gemma:2b || true
ollama pull nomic-embed-text || true
# Prefer a solid mid/large for worker; gemma2:27b or qwen2.5:32b if available
ollama pull gemma2:27b || ollama pull gemma2:9b || ollama pull llama3.1:8b || true

echo "Tags:"
curl -s http://127.0.0.1:11434/api/tags | head -c 2000
echo
echo "DONE. From your Windows Mag machine:"
echo "  ssh -N -L 11434:127.0.0.1:11434 root@VAST_IP -p VAST_PORT"
echo "  then: set OLLAMA_HOST=http://127.0.0.1:11434"
echo "  python main.py blast --status"
echo "  python main.py blast --run --bg"
echo "  open http://127.0.0.1:8765/ → BST tab"
