#!/bin/bash
# Vast on-start / provisioning script for Mag Ollama plant.
# Paste into template "On-start script" or run once via SSH.
# Target: RTX 8000 48GB class — see MODEL_STACK.md
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
LOG=/var/log/mag-ollama-onstart.log
exec > >(tee -a "$LOG") 2>&1

echo "[mag] onstart $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# --- Ollama ---
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi

# Serve on all interfaces (Vast port map / SSH local forward)
export OLLAMA_HOST="${OLLAMA_HOST:-0.0.0.0:11434}"
# Keep models warm longer during dig cycles
export OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-30m}"

# Kill stale serve if any
pkill -f "ollama serve" 2>/dev/null || true
sleep 1
nohup ollama serve >>/var/log/ollama-serve.log 2>&1 &
sleep 4

# Wait for API
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:11434/api/tags >/dev/null; then
    echo "[mag] ollama up"
    break
  fi
  sleep 2
done

# Stack select: rtx8000_48 (default) | tight70 | tiny
STACK="${MAG_STACK:-rtx8000_48}"
echo "[mag] MAG_STACK=$STACK"

pull() {
  echo "[mag] pull $1"
  ollama pull "$1" || echo "[mag] WARN pull failed: $1"
}

case "$STACK" in
  tiny)
    pull gemma:2b
    pull nomic-embed-text
    ;;
  tight70)
    # Single heavy worker — little room for concurrent models
    pull gemma:2b
    pull nomic-embed-text
    pull llama3.3:70b
    ;;
  rtx8000_48|*)
    # Optimized Mag blast default: room for context + embed
    pull gemma:2b
    pull nomic-embed-text
    # Primary worker — 32B class Q4 fits ~20GB, headroom for 16–32k ctx digs
    pull qwen2.5:32b || pull qwen2.5:14b || pull llama3.1:8b
    # Optional second mid for A/B (unload when not used)
    # pull qwen2.5-coder:32b
    ;;
esac

echo "[mag] tags:"
curl -s http://127.0.0.1:11434/api/tags | head -c 4000 || true
echo
echo "[mag] READY — tunnel from Mag host: ssh -N -L 11434:127.0.0.1:11434 ..."
echo "[mag] done $(date -u +%Y-%m-%dT%H:%M:%SZ)"
