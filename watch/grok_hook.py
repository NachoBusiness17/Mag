#!/usr/bin/env python3
"""Grok hook sink: append session events for the local agent to watch.

Called by ~/.grok/hooks with JSON on stdin. Always exits 0 (fail-open).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parents[1]
WATCH_DIR = AGENT_ROOT / "watch"
FEED = WATCH_DIR / "grok_feed.jsonl"
LIVE = AGENT_ROOT / "memory" / "live_from_grok.md"
POINTER = WATCH_DIR / "active_session.json"


def _preview(val, n: int = 500) -> str | None:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        s = json.dumps(val, default=str)
    else:
        s = str(val)
    return s.replace("\r", " ").strip()[:n]


def main() -> int:
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {"raw": raw[:4000], "parse_error": True}

    sid = (
        os.environ.get("GROK_SESSION_ID")
        or event.get("sessionId")
        or event.get("session_id")
    )
    hook_event = (
        os.environ.get("GROK_HOOK_EVENT")
        or event.get("hookEventName")
        or "unknown"
    )
    cwd = event.get("cwd") or event.get("workspaceRoot") or os.environ.get("GROK_CWD")

    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "hook_event": hook_event,
        "session_id": sid,
        "cwd": cwd,
        "tool_name": event.get("toolName") or event.get("tool_name"),
        "prompt_preview": _preview(
            event.get("prompt") or event.get("userPrompt") or event.get("text")
        ),
        "tool_input_preview": _preview(
            event.get("toolInput") or event.get("tool_input")
        ),
    }

    with FEED.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, default=str) + "\n")

    if sid:
        POINTER.write_text(
            json.dumps(
                {
                    "session_id": sid,
                    "cwd": cwd,
                    "updated_at": rec["ts"],
                    "last_hook": hook_event,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    LIVE.parent.mkdir(parents=True, exist_ok=True)
    LIVE.write_text(
        "\n".join(
            [
                "# Live from Grok",
                "",
                f"- **updated:** {rec['ts']}",
                f"- **session:** `{sid}`",
                f"- **last hook:** `{hook_event}`",
                f"- **cwd:** `{cwd}`",
                f"- **tool:** `{rec.get('tool_name')}`",
                "",
                "## Last prompt preview",
                "",
                "```",
                rec.get("prompt_preview") or "(none)",
                "```",
                "",
                "Feed: `watch/grok_feed.jsonl`. Full logs: `~/.grok/sessions/`.",
                "Run `python main.py watch` for continuous chat_history tail.",
                "On SessionEnd Mag writes `memory/biography/<session>.md`.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # SessionEnd also handled by session_end_hook.py (longer timeout + LLM).
    # Fallback if only this hook runs:
    he = (hook_event or "").lower().replace("_", "")
    if sid and he in {"sessionend", "session_end"}:
        try:
            sys.path.insert(0, str(AGENT_ROOT))
            from mag.biography import pack_status, summarize_session

            st = pack_status(sid)
            summarize_session(
                sid,
                cwd=cwd,
                use_llm=True,
                force=not st.get("complete"),
                pdf=False,
                visual=False,
                amend=True,
            )
            if not pack_status(sid).get("complete"):
                summarize_session(
                    sid,
                    cwd=cwd,
                    use_llm=False,
                    force=True,
                    pdf=False,
                    visual=False,
                    amend=True,
                )
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
