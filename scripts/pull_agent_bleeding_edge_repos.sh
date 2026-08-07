#!/usr/bin/env bash
# Pull bleeding-edge agent research repos into mine/raw/agent_bleeding_edge/
# Manifest: configs/agent_bleeding_edge_repos.yaml
# Optional Wave 2: MAG_BLEEDING_EDGE_WAVE2=1
# Optional stars: MAG_GH_STAR=1 + gh auth login

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${MAG_BLEEDING_EDGE_DEST:-${ROOT}/mine/raw/agent_bleeding_edge}"

REPOS=(
  "exo|https://github.com/exo-explore/exo.git|exo-explore/exo"
  "letta|https://github.com/letta-ai/letta.git|letta-ai/letta"
  "mem0|https://github.com/mem0ai/mem0.git|mem0ai/mem0"
  "oh-traj-viz|https://github.com/OpenHands/trajectory-visualizer.git|OpenHands/trajectory-visualizer"
  "agent-replay|https://github.com/clay-good/agent-replay.git|clay-good/agent-replay"
  "agentops|https://github.com/AgentOps-AI/agentops.git|AgentOps-AI/agentops"
  "phoenix|https://github.com/arize-ai/phoenix.git|arize-ai/phoenix"
  "a2a|https://github.com/a2aproject/A2A.git|a2aproject/A2A"
  "mcp-agent|https://github.com/lastmile-ai/mcp-agent.git|lastmile-ai/mcp-agent"
  "late-chunking|https://github.com/jina-ai/late-chunking.git|jina-ai/late-chunking"
  "zep|https://github.com/getzep/zep.git|getzep/zep"
  "sweep|https://github.com/sweepai/sweep.git|sweepai/sweep"
)

WAVE2=(
  "agentlens|https://github.com/agentlens-hq/agentlens.git|agentlens-hq/agentlens"
  "agentlens-observe|https://github.com/tranhoangtu-it/agentlens.git|tranhoangtu-it/agentlens"
  "agent-bazaar-stellar|https://github.com/Allen-Saji/agent-bazaar.git|Allen-Saji/agent-bazaar"
  "agent-bazaar-solana|https://github.com/Agent-Bazaar/Agent-Bazaar.git|Agent-Bazaar/Agent-Bazaar"
  "fixie-sdk|https://github.com/fixie-ai/fixie-sdk.git|fixie-ai/fixie-sdk"
)

mkdir -p "$DEST"
cd "$DEST"

pull_one() {
  local name="$1" url="$2" subdir="$3"
  local target="$subdir"
  mkdir -p "$(dirname "$target")"
  if [[ -d "$target/.git" ]]; then
    echo "==> pull $name ($target)"
    git -C "$target" pull --ff-only origin HEAD 2>/dev/null || git -C "$target" pull --ff-only
  else
    echo "==> clone $name -> $target"
    git -c core.longpaths=true clone --depth 1 "$url" "$target"
    git -C "$target" config core.longpaths true 2>/dev/null || true
  fi
  if [[ "${MAG_GH_STAR:-}" == "1" ]] && command -v gh >/dev/null 2>&1; then
    gh repo star "$subdir" 2>/dev/null || true
  fi
}

for entry in "${REPOS[@]}"; do
  IFS='|' read -r name url subdir <<< "$entry"
  pull_one "$name" "$url" "$subdir"
done

if [[ "${MAG_BLEEDING_EDGE_WAVE2:-}" == "1" ]]; then
  for entry in "${WAVE2[@]}"; do
    IFS='|' read -r name url subdir <<< "$entry"
    pull_one "$name" "$url" "$subdir"
  done
fi

echo "Done. Index: docs/ref/AGENT_BLEEDING_EDGE_REPOS_INDEX.md"
