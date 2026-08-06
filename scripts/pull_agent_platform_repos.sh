#!/usr/bin/env bash
# Pull agent-platform research repos into mine/raw/agent_platform/
# Manifest: configs/agent_platform_repos.yaml
# Optional Wave 2: MAG_AGENT_PLATFORM_WAVE2=1
# Optional stars: MAG_GH_STAR=1 + gh auth login

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${MAG_AGENT_PLATFORM_DEST:-${ROOT}/mine/raw/agent_platform}"

REPOS=(
  "openhands|https://github.com/OpenHands/OpenHands.git|OpenHands/OpenHands"
  "swe-agent|https://github.com/SWE-agent/SWE-agent.git|SWE-agent/SWE-agent"
  "aider|https://github.com/Aider-AI/aider.git|Aider-AI/aider"
  "jj|https://github.com/jj-vcs/jj.git|jj-vcs/jj"
  "litellm|https://github.com/BerriAI/litellm.git|BerriAI/litellm"
  "mcp-python|https://github.com/modelcontextprotocol/python-sdk.git|modelcontextprotocol/python-sdk"
  "continue|https://github.com/continuedev/continue.git|continuedev/continue"
  "melty|https://github.com/meltylabs/melty.git|meltylabs/melty"
  "pearai-sub|https://github.com/trypear/pearai-submodule.git|trypear/pearai-submodule"
  "mini-swe-agent|https://github.com/SWE-agent/mini-swe-agent.git|SWE-agent/mini-swe-agent"
  "opencode|https://github.com/anomalyco/opencode.git|anomalyco/opencode"
  "agent-worktree|https://github.com/nekocode/agent-worktree.git|nekocode/agent-worktree"
  "worktree-pilot|https://github.com/WorktreePilot/worktree-pilot.git|WorktreePilot/worktree-pilot"
  "agetor|https://github.com/alamops/agetor.git|alamops/agetor"
  "cline|https://github.com/cline/cline.git|cline/cline"
  "cline-kanban|https://github.com/cline/kanban.git|cline/kanban"
  "openharness|https://github.com/mifunedev/openharness.git|mifunedev/openharness"
  "runmaestro|https://github.com/RunMaestro/Maestro.git|RunMaestro/Maestro"
  "google-adk|https://github.com/google/adk-python.git|google/adk-python"
  "openai-agents|https://github.com/openai/openai-agents-python.git|openai/openai-agents-python"
)

WAVE2=(
  "void|https://github.com/voideditor/void.git|voideditor/void"
  "aide|https://github.com/codestoryai/aide.git|codestoryai/aide"
  "sidecar|https://github.com/codestoryai/sidecar.git|codestoryai/sidecar"
  "sapling|https://github.com/facebook/sapling.git|facebook/sapling"
  "opentree|https://github.com/axelgar/opentree.git|axelgar/opentree"
  "emd-maestro|https://github.com/emdgroup/maestro.git|emdgroup/maestro"
  "kankanban|https://github.com/Knwar/kankanban.git|Knwar/kankanban"
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
    git clone --depth 1 "$url" "$target"
  fi
  if [[ "${MAG_GH_STAR:-}" == "1" ]] && command -v gh >/dev/null 2>&1; then
    gh repo star "$subdir" 2>/dev/null || true
  fi
}

for entry in "${REPOS[@]}"; do
  IFS='|' read -r name url subdir <<< "$entry"
  pull_one "$name" "$url" "$subdir"
done

if [[ "${MAG_AGENT_PLATFORM_WAVE2:-}" == "1" ]]; then
  for entry in "${WAVE2[@]}"; do
    IFS='|' read -r name url subdir <<< "$entry"
    pull_one "$name" "$url" "$subdir"
  done
fi

echo "Done. Index: docs/ref/AGENT_PLATFORM_REPOS_INDEX.md"
