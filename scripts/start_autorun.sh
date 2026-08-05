#!/usr/bin/env bash
# Start Mag autorun drainer (intelligent queue + governor).
# Prereq: lab on :8765, backend on :8000, keys in .env
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || { echo "missing .venv — run scripts/ensure_venv.ps1 or pip install -r requirements.txt"; exit 1; }

export MAG_DRAINER="${MAG_DRAINER:-1}"
export MAG_OPERATOR_ACTIVE="${MAG_OPERATOR_ACTIVE:-0}"

echo "[start_autorun] doctor..."
"$PY" main.py doctor | head -5

echo "[start_autorun] routing smoke..."
"$PY" scripts/routing_smoke.py

echo "[start_autorun] enabling drainer pref..."
"$PY" -c "from mag.preferences import set_drainer; set_drainer(True)"

echo "[start_autorun] launching autorun loop (Ctrl-C to stop)..."
exec "$PY" main.py autorun --interval "${MAG_AUTORUN_INTERVAL:-10}"
