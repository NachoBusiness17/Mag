#!/usr/bin/env bash
# Mag v3 DeepSeek code run — queue one build goal and drain once.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python

echo ""
echo "=== Mag v3 DeepSeek code run ==="

if [[ -z "${DEEPSEEK_API_KEY:-}" ]] && [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env" 2>/dev/null || true
  set +a
fi
if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "[FAIL] DEEPSEEK_API_KEY not set — copy .env.example to .env"
  exit 1
fi
echo "[OK] DeepSeek key present"

GOAL="${*:-[build] execute frozen queue/handoff/BUILD-v3-deepseek-proof.md exactly}"

echo "[1/7] doctor..."
"$PY" main.py doctor >/dev/null

echo "[2/7] routing smoke..."
"$PY" scripts/routing_smoke.py >/dev/null

echo "[3/7] v3-status..."
"$PY" main.py v3-status >/dev/null

echo "[4/7] power start..."
"$PY" main.py power start --json | grep -q '"ok": true'

echo "[5/7] seat register..."
"$PY" main.py seats register --seat cursor --goal "v3 deepseek run" --json >/dev/null

echo "[6/7] frozen DeepSeek run..."
echo "  Goal: $GOAL"
"$PY" main.py orchestrator run "$GOAL" --provider deepseek --tag v3-deepseek-run --timeout 300 --wait | grep -q '"status": "done"'

echo "[7/7] improve-loop + spider..."
"$PY" main.py improve-loop cycle --json | grep -q improve_loop
"$PY" main.py spider --once >/dev/null
"$PY" main.py training-events --stats

echo ""
echo "[PASS] v3 DeepSeek run started"
echo "  Drain again: $PY main.py orchestrator drain --once"
echo "  Kill stack:  $PY main.py power stop"
