"""Write mesh forest INTEGRATION_BRIEF.md for local agent deep dive."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "mine" / "raw" / "mesh_comm"
BRIEF = ROOT / "memory" / "research_packs" / "mesh_forest" / "INTEGRATION_BRIEF.md"

REPOS = [
    ("permissionlesstech", "bitchat", "Dual transport BLE→Nostr; WHITEPAPER.md; MessageRouter"),
    ("permissionlesstech", "bitchat-android", "UnifiedMeshService; Wi-Fi Aware; binary protocol"),
    ("permissionlesstech", "georelays", "Nostr relay crawl — hub topology research only"),
    ("bridgefy", "sdk-android", "P2P/Mesh/Broadcast; propagation profiles"),
    ("bridgefy", "sdk-ios", "iOS mesh SDK parity"),
    ("bridgefy", "bridgefy_flutter", "Flutter propagation enum"),
    ("bridgefy", "bridgefy-react-native", "RN TurboModule; top org repo"),
    ("bridgefy", "sdk-android-beta", "Beta API drift vs stable"),
    ("bridgefy", "sdk-ios-beta", "Beta API drift vs stable"),
    ("briar", "briar", "Sync without server; Tor + BT/Wi-Fi"),
    ("briar", "briar-mailbox", "Optional willing relay mailbox"),
    ("briar", "briar-desktop", "Desktop peer sync"),
    ("briar", "onionwrapper", "Tor transport library"),
]


def main() -> None:
    BRIEF.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Mesh forest — integration brief (local agent)",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "**Use with:** `mag.cmd agent` · spores: `docs/ref/spores/mesh/`",
        "",
        "## Clones (read via agent read_file)",
        "",
        "| Org | Path | Steal focus |",
        "|-----|------|-------------|",
    ]
    for org, repo, focus in REPOS:
        rel = f"mine/raw/mesh_comm/{org}/{repo}"
        ok = "✓" if (DEST / org / repo).is_dir() else "✗ missing"
        lines.append(f"| {org} | `{rel}` {ok} | {focus} |")

    lines += [
        "",
        "## Filed spores (Mag contracts — start here)",
        "",
        "- `docs/ref/spores/mesh/bitchat-dual-transport-20260805.md`",
        "- `docs/ref/spores/mesh/bridgefy-transmission-modes-20260805.md`",
        "- `docs/ref/spores/mesh/briar-sync-no-server-20260805.md`",
        "",
        "## Agent goals (copy-paste)",
        "",
        "1. **Architecture map** — For each org, read README + key `*Router*`, `*Mesh*`, `*Sync*` sources.",
        "2. **Mag overlap** — Map to conductor transport_chain, pigeonhole modes, switchboard steer_drop.",
        "3. **Reject list** — UI, Nostr stack, silent mesh, GPL merge into Mag core.",
        "4. **Wire list** — Playbook lines for v4/v5 with willing L3 enroll gate.",
        "",
        "## Key upstream docs",
        "",
        "- `mine/raw/mesh_comm/permissionlesstech/bitchat/WHITEPAPER.md`",
        "- `mine/raw/mesh_comm/permissionlesstech/bitchat/README.md`",
        "- `mine/raw/mesh_comm/permissionlesstech/bitchat-android/README.md`",
        "",
        "## field-steal ledgers",
        "",
        "`memory/improve/field_steal/` (operator soil)",
        "",
    ]
    BRIEF.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {BRIEF}")


if __name__ == "__main__":
    main()
