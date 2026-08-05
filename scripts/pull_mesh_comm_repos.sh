#!/usr/bin/env bash
# Pull mesh / offline comm research repos into mine/raw/mesh_comm/ (Mag-native soil).
# Safe to re-run: clones missing dirs, git pull --ff-only in existing ones.
#
# Index: docs/ref/MESH_COMM_REPOS_INDEX.md
# Manifest: configs/mesh_comm_repos.yaml

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${MAG_MESH_DEST:-${ROOT}/mine/raw/mesh_comm}"

# id|clone_url|subdir (owner/repo as path)
REPOS=(
  "bitchat|https://github.com/permissionlesstech/bitchat.git|permissionlesstech/bitchat"
  "bitchat-android|https://github.com/permissionlesstech/bitchat-android.git|permissionlesstech/bitchat-android"
  "georelays|https://github.com/permissionlesstech/georelays.git|permissionlesstech/georelays"
  "bridgefy-android|https://github.com/bridgefy/sdk-android.git|bridgefy/sdk-android"
  "bridgefy-ios|https://github.com/bridgefy/sdk-ios.git|bridgefy/sdk-ios"
  "bridgefy-flutter|https://github.com/bridgefy/bridgefy_flutter.git|bridgefy/bridgefy_flutter"
  "bridgefy-react-native|https://github.com/bridgefy/bridgefy-react-native.git|bridgefy/bridgefy-react-native"
  "bridgefy-android-beta|https://github.com/bridgefy/sdk-android-beta.git|bridgefy/sdk-android-beta"
  "bridgefy-ios-beta|https://github.com/bridgefy/sdk-ios-beta.git|bridgefy/sdk-ios-beta"
  "briar|https://github.com/briar/briar.git|briar/briar"
  "briar-mailbox|https://github.com/briar/briar-mailbox.git|briar/briar-mailbox"
  "briar-desktop|https://github.com/briar/briar-desktop.git|briar/briar-desktop"
  "briar-onionwrapper|https://github.com/briar/onionwrapper.git|briar/onionwrapper"
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
done

# Write pull manifest (operator soil — under gitignored tree)
MANIFEST="$DEST/_pull_manifest.json"
python3 - <<'PY' "$MANIFEST" "$DEST"
import json, sys
from datetime import datetime, timezone
from pathlib import Path
dest = Path(sys.argv[2])
rows = []
for p in sorted(dest.rglob(".git")):
    repo = p.parent
    rel = repo.relative_to(dest).as_posix()
    rows.append({"path": rel, "exists": True})
out = {
    "schema": "mesh_comm_pull_manifest.v1",
    "ts": datetime.now(timezone.utc).isoformat(),
    "dest": str(dest),
    "repos": rows,
    "count": len(rows),
}
Path(sys.argv[1]).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {sys.argv[1]} ({len(rows)} repos)")
PY

echo "Done. Index: docs/ref/MESH_COMM_REPOS_INDEX.md"
