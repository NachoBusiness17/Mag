#!/usr/bin/env python3
"""CLI shim — logic in mag/ponytail_audit.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mag.ponytail_audit import format_report, run_audit  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Ponytail ladder audit for Mag")
    p.add_argument("--json", action="store_true")
    p.add_argument("--fix-hints", action="store_true")
    args = p.parse_args(argv)
    res = run_audit(hints=args.fix_hints)
    print(json.dumps(res, indent=2) if args.json else format_report(res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
