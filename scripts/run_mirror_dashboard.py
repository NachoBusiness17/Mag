#!/usr/bin/env python3
"""Launch Sovereign Mirror strike desk on :8743 (optional co-spawn with Mag)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

MAG_ROOT = Path(__file__).resolve().parents[1]


def _mirror_home() -> Path | None:
    env = os.environ.get("MAG_MIRROR_HOME", "").strip()
    if env:
        p = Path(env)
        return p if (p / "src" / "sovereign_mirror").is_dir() else None
    for cand in (
        MAG_ROOT.parent / "worktrees" / "sovereign-mirror-scaffold",
        MAG_ROOT.parent / "sovereign-mirror-scaffold",
    ):
        if (cand / "src" / "sovereign_mirror" / "dashboard" / "server.py").is_file():
            return cand
    return None


def main(argv: list[str] | None = None) -> int:
    home = _mirror_home()
    if not home:
        print("mirror: scaffold not found (set MAG_MIRROR_HOME)", file=sys.stderr)
        return 0
    src = home / "src"
    sys.path.insert(0, str(src))
    os.environ.setdefault("MAG_HOME", str(MAG_ROOT))
    os.environ.setdefault("SOVEREIGN_MAG_HOME", str(MAG_ROOT))
    from sovereign_mirror.dashboard.server import main as mirror_main

    args = list(argv or sys.argv[1:])
    if "--port" not in args and "-p" not in args:
        args = ["--port", "8743", "--no-browser", *args]
    elif "--no-browser" not in args:
        args.append("--no-browser")
    return int(mirror_main(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
