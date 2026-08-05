"""Build survival portable bag — configs, spores, briefs, integration brief."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAGS = ROOT / "memory" / "portable_bags"

# Paths relative to repo root — cold reboot kit
INCLUDE = [
    "docs/FRAMEWORK_LOAD.md",
    "docs/DNA.md",
    "docs/ref/OPERATOR_CARD.md",
    "docs/ref/OPERATOR_SURVIVAL_EXTRACT.md",
    "docs/ref/MESH_LOCAL_AGENT.md",
    "docs/ref/MESH_COMM_REPOS_INDEX.md",
    "docs/ref/MAG_ILAP_PROTOCOL.md",
    "docs/ref/MAG_v5_MESH_FOREST.md",
    "docs/ref/MAG_DIRECTION_ARTIFACT_v2.md",
    "docs/ref/MAG_NEXT_CODING_RUN.md",
    "configs/mesh_comm_repos.yaml",
    "configs/modules.yaml",
    "configs/improve.yaml",
    "memory/operator_directives.md",
    "AGENTS.md",
    "CONSTITUTION.md",
]

INCLUDE_DIRS = [
    "docs/ref/spores/mesh",
    "docs/ref/proposals",
    "memory/research_packs/mesh_forest",
]


def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bag = BAGS / f"survival-{ts}"
    bag.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str]] = []

    for rel in INCLUDE:
        src = ROOT / rel
        if not src.is_file():
            continue
        dst = bag / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        manifest.append({"path": rel, "kind": "file"})

    for rel in INCLUDE_DIRS:
        src = ROOT / rel
        if not src.is_dir():
            continue
        dst = bag / rel
        shutil.copytree(src, dst, dirs_exist_ok=True)
        manifest.append({"path": rel, "kind": "dir"})

    # Pointer for os_v2 / operator
    ptr = BAGS / "LATEST.txt"
    ptr.write_text(f"survival-{ts}\n", encoding="utf-8")

    meta = {
        "schema": "portable_bag.v1",
        "id": f"survival-{ts}",
        "ts": datetime.now(timezone.utc).isoformat(),
        "entries": manifest,
        "note": "Lessig move 6 — cold reboot without cloud. Clones stay in mine/raw (copy separately).",
    }
    (bag / "MANIFEST.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Bag: {bag}")
    print(f"Entries: {len(manifest)}")
    print(f"Pointer: {ptr}")


if __name__ == "__main__":
    main()
