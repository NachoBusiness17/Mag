#!/usr/bin/env python3
"""Grok SessionStart: Sancho boot (self-analysis + ensure Mag lab).

Fail-open: always exit 0. Writes memory/boot_report.md + watch/boot_latest.json.
Also runs the light feed hook so active_session is set.
"""
from __future__ import annotations

import sys
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_ROOT))


def main() -> int:
    # 1) Feed sink first (stdin may be consumed by grok_hook)
    try:
        from watch.grok_hook import main as feed_main

        feed_main()
    except Exception:
        pass

    # 2) Boot card + ensure lab if down
    try:
        from mag.boot import run_boot

        report = run_boot(ensure=True, light=True)
        # stdout may surface in hook debug; keep short
        text = (report.get("text") or "")[:1500]
        print(text)
    except Exception as e:
        err = AGENT_ROOT / "logs" / "boot_errors.log"
        err.parent.mkdir(parents=True, exist_ok=True)
        with err.open("a", encoding="utf-8") as f:
            f.write(f"{e}\n")
        print(f"Sancho boot failed (fail-open): {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
