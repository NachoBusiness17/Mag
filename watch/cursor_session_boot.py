#!/usr/bin/env python3
"""Cursor session boot — register seat with orchestrator mesh (sessionStart hook).

Called from .cursor/hooks.json on sessionStart. No stdin required.
Always exits 0 so Cursor never blocks.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WATCH = ROOT / "watch"
BOOT_LOG = WATCH / "cursor_session_boot.jsonl"


def _log(event: str, **fields) -> None:
    WATCH.mkdir(parents=True, exist_ok=True)
    row = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    with BOOT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def main() -> int:
    sid = os.environ.get("CURSOR_SESSION_ID", "").strip() or "cursor-desktop"
    cwd = os.environ.get("CURSOR_CWD", "").strip() or str(ROOT)
    os.environ["MAG_OPERATOR_ACTIVE"] = "1"

    rec: dict = {"ok": False, "session_id": sid}
    try:
        from mag.seat_registry import register

        rec = register(
            seat="cursor",
            goal=f"Cursor session {sid[:12]}",
            mode="interactive",
            parent="cursor_hook",
            tag="cursor-desktop",
        )
        tid = rec.get("task_id") or ""
        if tid:
            os.environ["MAG_TASK_ID"] = tid
            WATCH.mkdir(parents=True, exist_ok=True)
            POINTER = WATCH / "active_cursor_session.json"
            POINTER.write_text(
                json.dumps(
                    {
                        "session_id": sid,
                        "task_id": tid,
                        "mag_task_id": tid,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "seat": "cursor",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            _log("register", task_id=tid, session_id=sid)
    except Exception as exc:
        _log("register_error", error=str(exc)[:200], session_id=sid)
        return 0

    try:
        from mag.operator_inbox import log_behavioral_event

        log_behavioral_event(
            kind="session_start",
            detail=f"Cursor desktop session registered task_id={rec.get('task_id')}",
            session_id=sid,
            provider="cursor",
            phase="registered",
        )
    except Exception:
        pass

    try:
        preamble = ROOT / "memory" / "cursor_preamble_latest.md"
        if not preamble.is_file():
            from mag.context_pack import build_context_pack, format_agent_preamble

            pack = build_context_pack(max_brief=900, max_live=400)
            preamble.write_text(
                format_agent_preamble(pack, goal="Cursor session — restful seat on Mag boundary"),
                encoding="utf-8",
            )
    except Exception:
        pass

    _log("boot_ok", task_id=rec.get("task_id"), cwd=cwd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
