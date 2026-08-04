#!/usr/bin/env python
"""Offline test for the governor stall-nudge (mag/supervisor.py + orchestrator wiring).

No model calls, no provider keys, ~2 seconds. Simulates a sub-agent that stops
heartbeating and proves the full receipt-nudge path the same way the live
orchestrator monitor would:

    staleness detected -> stall_nudge_text(task_id, age) builds receipts
    -> ph.post_steer writes "!steer <nudge>" to the task's inbox
    -> orchestrator trails event stall-nudge receipts=True
    -> drain_inbox() returns the steer, exactly like the sub-agent's
       _drain_steer_until() loop would consume it (then apply_steer injects).

Usage:  python scripts/test_stall_nudge.py
"""
from __future__ import annotations
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mag import pigeonhole as ph          # noqa: E402
from mag import supervisor as sup          # noqa: E402
from mag import orchestrator as o          # noqa: E402

TASK_ID = "tstall-demo"


def make_task_record() -> None:
    """Minimal task record so stall_nudge_text can include the goal receipt."""
    o._ensure_dirs()
    rec = {
        "task_id": TASK_ID,
        "goal": "Fetch and unpack the DeepSeek share into a dig leaf",
        "cmd": ["python", "main.py", "agent", "--query", "unpack"],
        "status": "running",
        "created_at": o._now(),
    }
    o._save(rec)


def main() -> int:
    # clean slate
    shutil.rmtree(ph.mailbox_dir(TASK_ID), ignore_errors=True)
    o._task_path(TASK_ID).unlink(missing_ok=True)

    make_task_record()

    print("=" * 64)
    print("GOVERNOR STALL-NUDGE OFFLINE TEST")
    print("=" * 64)

    # 1. agent boots, writes heartbeats + status (fresh)
    ph.heartbeat(TASK_ID, step=1, last_tool="run_python", phase="working")
    ph.heartbeat(TASK_ID, step=2, last_tool="run_shell", phase="working")
    ph.write_status(TASK_ID, phase="working")
    print("[1] agent heartbeat written (step 2, last_tool=run_shell)")
    print("    stall threshold STALL_AFTER_S =", ph.STALL_AFTER_S, "s")

    # 2. agent goes quiet mid-tool (no more beads). Simulate by backdating the
    #    heartbeat file mtime -- that is exactly what staleness_s() reads.
    quiet_for = ph.STALL_AFTER_S + 12
    now = time.time()
    bead = ph.mailbox_dir(TASK_ID) / "heartbeat.jsonl"
    os.utime(bead, (now - quiet_for, now - quiet_for))
    age = ph.staleness_s(TASK_ID)
    print(f"[2] agent silent for {quiet_for}s (backdated bead) -> staleness_s = {age}s")

    # 3. orchestrator monitor hits poll 2 past threshold -> build + post nudge
    text = sup.stall_nudge_text(TASK_ID, age)
    assert text, "nudge text must not be empty"
    assert "unpack" in text, "nudge must carry the goal receipt"
    assert "timed out" in text, "nudge must carry timeout guidance"
    print("[3] nudge built from receipts (%d chars):" % len(text))
    for ln in text.splitlines():
        print("    | " + ln)

    ph.post_steer(TASK_ID, text)
    o._trail("stall-nudge", TASK_ID, age_s=age, receipts=True)
    print("[4] posted to mailbox inbox.txt + trail event 'stall-nudge'")

    # 4. sub-agent's mid-round drain loop picks it up
    cmds = ph.drain_inbox(TASK_ID)
    assert cmds, "inbox must contain the steer"
    steer = cmds[0]
    assert steer.startswith("!steer "), steer
    print("[5] sub-agent drain_inbox() returned:", steer[:60] + "...")

    # 5. trail shows the receipt event (what the operator can grep)
    tail = []
    if o.TRAIL.is_file():
        with o.TRAIL.open(encoding="utf-8") as fh:
            for ln in fh:
                if TASK_ID in ln:
                    tail.append(ln.strip())
    ev = json.loads(tail[-1]) if tail else {}
    print("[6] trail tail:", json.dumps(ev, ensure_ascii=False)[:160])
    assert ev.get("event") == "stall-nudge" and ev.get("receipts") is True

    # cleanup
    shutil.rmtree(ph.mailbox_dir(TASK_ID), ignore_errors=True)
    o._task_path(TASK_ID).unlink(missing_ok=True)
    print("\nPASS: full receipt-nudge path verified (no model call needed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
