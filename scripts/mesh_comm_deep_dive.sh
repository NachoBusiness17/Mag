#!/usr/bin/env bash
# Mesh forest deep dive — all 13 clones, field-steal each, integration brief for local agent.
# Scout (3 repos): mesh_comm_ilap_run.sh · This script: full corpus for mag.cmd agent

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${MAG_PYTHON:-${ROOT}/.venv/bin/python}"
DEST="${MAG_MESH_DEST:-${ROOT}/mine/raw/mesh_comm}"
BRIEF_DIR="${ROOT}/memory/research_packs/mesh_forest"

# id|relative clone path under mesh_comm
REPOS=(
  "bitchat|permissionlesstech/bitchat"
  "bitchat-android|permissionlesstech/bitchat-android"
  "georelays|permissionlesstech/georelays"
  "bridgefy-android|bridgefy/sdk-android"
  "bridgefy-ios|bridgefy/sdk-ios"
  "bridgefy-flutter|bridgefy/bridgefy_flutter"
  "bridgefy-react-native|bridgefy/bridgefy-react-native"
  "bridgefy-android-beta|bridgefy/sdk-android-beta"
  "bridgefy-ios-beta|bridgefy/sdk-ios-beta"
  "briar|briar/briar"
  "briar-mailbox|briar/briar-mailbox"
  "briar-desktop|briar/briar-desktop"
  "briar-onionwrapper|briar/onionwrapper"
)

cd "$ROOT"
echo "==> mesh deep dive: pull clones"
"${ROOT}/scripts/pull_mesh_comm_repos.sh"

mkdir -p "$BRIEF_DIR"
STEAL_LOG="${BRIEF_DIR}/field_steal_runs.txt"
: > "$STEAL_LOG"

echo "==> field-steal all repos"
for entry in "${REPOS[@]}"; do
  IFS='|' read -r name subdir <<< "$entry"
  target="${DEST}/${subdir}"
  if [[ ! -d "$target" ]]; then
    echo "skip $name — missing $target" | tee -a "$STEAL_LOG"
    continue
  fi
  echo "==> steal $name — $subdir" | tee -a "$STEAL_LOG"
  "$PY" main.py field-steal --root "$target" --max-files 35 2>&1 | tail -3 | tee -a "$STEAL_LOG" || true
done

echo "==> integration brief"
"$PY" "${ROOT}/scripts/_mesh_integration_brief.py"

echo ""
echo "Done. Next:"
echo "  $PY main.py agent --provider deepseek"
echo "  Goal: Read memory/research_packs/mesh_forest/INTEGRATION_BRIEF.md and build Mag integration map."
echo "  Index: docs/ref/MESH_COMM_REPOS_INDEX.md · Guide: docs/ref/MESH_LOCAL_AGENT.md"
