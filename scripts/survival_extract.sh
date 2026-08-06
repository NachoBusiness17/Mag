#!/usr/bin/env bash
# Survival extract — pull everything local before cloud rent ends.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${MAG_PYTHON:-${ROOT}/.venv/bin/python}"
BRANCH="${1:-cursor/mesh-comm-research-e2ce}"

cd "$ROOT"
echo "[survival] repo: $ROOT"
echo "[survival] branch: $BRANCH"

git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH" || true

"${ROOT}/scripts/pull_mesh_comm_repos.sh"
[[ -x "${ROOT}/scripts/pull_gstdcoin_repos.sh" ]] && "${ROOT}/scripts/pull_gstdcoin_repos.sh" || true
[[ -x "${ROOT}/scripts/pull_steal_protocol_repos.sh" ]] && "${ROOT}/scripts/pull_steal_protocol_repos.sh" || true
"${ROOT}/scripts/mesh_comm_deep_dive.sh"
"$PY" "${ROOT}/scripts/_survival_bag.py"
"$PY" main.py context-pack --mode full || true
"$PY" main.py doctor || true

echo ""
echo "=== SURVIVAL EXTRACT DONE ==="
echo "Guide: docs/ref/OPERATOR_SURVIVAL_EXTRACT.md"
echo "Bag: $(cat memory/portable_bags/LATEST.txt 2>/dev/null || echo missing)"
