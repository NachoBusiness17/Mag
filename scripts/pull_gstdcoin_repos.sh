#!/usr/bin/env bash
# Pull all public gstdcoin org repos into reference/gstdcoin/ for local inspiration.
# Safe to re-run: clones missing dirs, git pull --ff-only in existing ones.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${ROOT}/reference/gstdcoin"
ORG="https://github.com/gstdcoin"
REPOS=(ai web A2A gstd-bridge gstdbot contracts)

mkdir -p "$DEST"
cd "$DEST"

for repo in "${REPOS[@]}"; do
  if [[ -d "$repo/.git" ]]; then
    echo "==> pull $repo"
    git -C "$repo" pull --ff-only origin HEAD 2>/dev/null || git -C "$repo" pull --ff-only
  else
    echo "==> clone $repo"
    git clone --depth 1 "${ORG}/${repo}.git" "$repo"
  fi
done

echo "Done. Index: docs/ref/GSTDCOIN_REPOS_INDEX.md"
