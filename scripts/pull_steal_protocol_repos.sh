#!/usr/bin/env bash
# Pull steal-protocol research repos into mine/raw/steal_protocol/
# Manifest: configs/steal_protocol_repos.yaml
# Optional stars: MAG_GH_STAR=1 + gh auth login

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${MAG_STEAL_DEST:-${ROOT}/mine/raw/steal_protocol}"

REPOS=(
  "agentswarm|https://github.com/robzilla1738/agentswarm.git|robzilla1738/agentswarm"
  "bmas|https://github.com/arvarik/bmas.git|arvarik/bmas"
  "flock|https://github.com/whiteducksoftware/flock.git|whiteducksoftware/flock"
  "blackboard-core|https://github.com/hemantsingh443/blackboard-core.git|hemantsingh443/blackboard-core"
  "ollama-agent-harness|https://github.com/Bradliebs/ollama-agent-harness.git|Bradliebs/ollama-agent-harness"
  "subagent-router|https://github.com/marikarx/subagent-router.git|marikarx/subagent-router"
  "leeroo-orchestrator|https://github.com/Leeroo-AI/leeroo_orchestrator.git|Leeroo-AI/leeroo_orchestrator"
  "c3|https://github.com/EIT-EAST-Lab/C3.git|EIT-EAST-Lab/C3"
  "moa|https://github.com/togethercomputer/moa.git|togethercomputer/moa"
  "ms-conductor|https://github.com/microsoft/conductor.git|microsoft/conductor"
  "agent-blackboard|https://github.com/claudioed/agent-blackboard.git|claudioed/agent-blackboard"
)

mkdir -p "$DEST"
cd "$DEST"

for entry in "${REPOS[@]}"; do
  IFS='|' read -r name url subdir <<< "$entry"
  target="$subdir"
  mkdir -p "$(dirname "$target")"
  if [[ -d "$target/.git" ]]; then
    echo "==> pull $name ($target)"
    git -C "$target" pull --ff-only origin HEAD 2>/dev/null || git -C "$target" pull --ff-only
  else
    echo "==> clone $name -> $target"
    git clone --depth 1 "$url" "$target"
  fi
  if [[ "${MAG_GH_STAR:-}" == "1" ]] && command -v gh >/dev/null 2>&1; then
    gh repo star "$subdir" 2>/dev/null || true
  fi
done

echo "Done. Index: docs/ref/STEAL_PROTOCOL_REPOS_INDEX.md"
