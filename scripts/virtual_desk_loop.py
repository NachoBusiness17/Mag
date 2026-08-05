#!/usr/bin/env python3
"""Run Mag virtual desk DeepSeek research loop (wrapper for main.py)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    py = ROOT / ".venv" / "bin" / "python"
    if not py.is_file():
        py = Path(sys.executable)
    cmd = [str(py), str(ROOT / "main.py"), "virtual-desk-loop", *sys.argv[1:]]
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
