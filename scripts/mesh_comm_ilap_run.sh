#!/usr/bin/env bash
# ILAP mesh forest scout — one command, no operator babysitting.
# Pull clones → field-steal → research-pack → routing_smoke → training_events

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${MAG_PYTHON:-${ROOT}/.venv/bin/python}"
cd "$ROOT"

echo "==> ILAP mesh scout"
"${ROOT}/scripts/pull_mesh_comm_repos.sh"

echo "==> field-steal bitchat"
"$PY" main.py field-steal --root mine/raw/mesh_comm/permissionlesstech/bitchat --max-files 40

echo "==> field-steal bridgefy"
"$PY" main.py field-steal --root mine/raw/mesh_comm/bridgefy/sdk-android --max-files 30

echo "==> field-steal briar"
"$PY" main.py field-steal --root mine/raw/mesh_comm/briar/briar --max-files 30

echo "==> research-pack whitepaper"
"$PY" main.py research-pack \
  --ask "Dual transport MessageRouter BLE mesh Nostr fallback — contracts for Mag switchboard" \
  --url "https://raw.githubusercontent.com/permissionlesstech/bitchat/main/WHITEPAPER.md" || true

echo "==> improve scout"
"$PY" main.py improve --once || true

echo "==> aim routing_smoke"
"$PY" scripts/routing_smoke.py

echo "==> training events"
"$PY" - <<'PY'
from mag.training_events import emit

emit("research_dive", join={"build_slug": "mesh-forest", "session_id": "ilap-mesh-scout", "source": "mesh_comm"},
     input_data={"sources": ["bitchat", "bridgefy", "briar"], "leaves": 3},
     outcome={"leaf_kind": "feature_compose_card", "paths": ["docs/ref/spores/mesh/"]},
     pattern_tags=["steal_compose", "mesh_ble", "dual_transport"])

emit("ilap_cycle", join={"build_slug": "mesh-forest", "commitment": "ilap-mesh-steal-001"},
     input_data={"routing_smoke": "pass", "overlap_action": "wire"},
     outcome={"waste_kind": "ok", "action_taken": "wire_only"},
     pattern_tags=["ilap_cycle"])
print("training events emitted")
PY

echo "Done. Spores: docs/ref/spores/mesh/ · Index: docs/ref/MESH_COMM_REPOS_INDEX.md"
