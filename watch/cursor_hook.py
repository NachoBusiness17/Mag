#!/usr/bin/env python3
"""Cursor IDE hook sink: append session events for Mag to watch.

Called by .cursor/hooks on sessionStart/sessionEnd. JSON on stdin. Always exits 0.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parents[1]
WATCH_DIR = AGENT_ROOT / "watch"
FEED = WATCH_DIR / "cursor_feed.jsonl"
LIVE = AGENT_ROOT / "memory" / "live_from_cursor.md"
POINTER = WATCH_DIR / "active_cursor_session.json"
AGENT_SESS_DIR = AGENT_ROOT / "memory" / "agent_sessions"


def _local_id(sid: str) -> str:
    safe = (sid or "default").strip().replace("/", "_")[:48] or "default"
    return f"cursor-{safe}"


def _materialize_session(sid: str, cwd: str | None) -> Path | None:
    """Turn cursor_feed lines for this session into agent_sessions JSON for biographer."""
    if not sid or not FEED.is_file():
        return None
    msgs: list[dict[str, str]] = []
    try:
        for line in FEED.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if str(rec.get("session_id") or "") != sid:
                continue
            hook = str(rec.get("hook_event") or "")
            if rec.get("prompt_preview"):
                msgs.append({"role": "user", "content": rec["prompt_preview"]})
            if rec.get("response_preview"):
                msgs.append({"role": "assistant", "content": rec["response_preview"]})
            elif hook.lower().replace("_", "") in {"sessionstart", "sessionend", "stop"}:
                msgs.append({"role": "system", "content": f"hook={hook} ts={rec.get('ts')}"})
    except (json.JSONDecodeError, OSError):
        return None
    if not msgs:
        return None
    AGENT_SESS_DIR.mkdir(parents=True, exist_ok=True)
    local = _local_id(sid)
    path = AGENT_SESS_DIR / f"{local}.json"
    payload = {
        "session_id": local,
        "provider": "cursor",
        "model": "composer",
        "cwd": cwd,
        "messages": msgs[-80:],
        "source": "cursor",
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


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

    hook_event = (
        os.environ.get("CURSOR_HOOK_EVENT")
        or event.get("hookEventName")
        or event.get("event")
        or "unknown"
    )
    sid = (
        os.environ.get("CURSOR_SESSION_ID")
        or event.get("conversationId")
        or event.get("sessionId")
        or event.get("session_id")
        or event.get("composerId")
    )
    cwd = (
        event.get("workspaceRoot")
        or event.get("cwd")
        or event.get("workspaceFolder")
        or os.environ.get("CURSOR_CWD")
    )

    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "hook_event": hook_event,
        "session_id": sid,
        "cwd": cwd,
        "model": event.get("model") or event.get("modelName"),
        "prompt_preview": _preview(
            event.get("prompt")
            or event.get("userPrompt")
            or event.get("text")
            or event.get("userMessage")
        ),
        "response_preview": _preview(
            event.get("response") or event.get("assistantMessage") or event.get("text")
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
                    "seat": "cursor",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    LIVE.parent.mkdir(parents=True, exist_ok=True)
    LIVE.write_text(
        "\n".join(
            [
                "# Live from Cursor",
                "",
                f"- **updated:** {rec['ts']}",
                f"- **session:** `{sid}`",
                f"- **last hook:** `{hook_event}`",
                f"- **cwd:** `{cwd}`",
                f"- **model:** `{rec.get('model')}`",
                "",
                "## Last prompt preview",
                "",
                "```",
                rec.get("prompt_preview") or "(none)",
                "```",
                "",
                "Feed: `watch/cursor_feed.jsonl`. Preamble: `memory/cursor_preamble_latest.md`.",
                "On sessionEnd Mag writes biography via `summarize-session --source cursor`.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    he = (hook_event or "").lower().replace("_", "").replace("-", "")
    if sid and he in {"sessionend", "stop", "composerstop"}:
        try:
            sys.path.insert(0, str(AGENT_ROOT))
            tid = os.environ.get("MAG_TASK_ID", "").strip()
            if not tid:
                ptr = POINTER.read_text(encoding="utf-8") if POINTER.is_file() else "{}"
                try:
                    tid = str(json.loads(ptr).get("task_id") or "")
                except Exception:
                    tid = ""
            if tid:
                from mag.seat_registry import unregister

                unregister(tid, status="done", detail=f"cursor hook {hook_event}")
        except Exception:
            pass
        try:
            sys.path.insert(0, str(AGENT_ROOT))
            from mag.biography import pack_status, summarize_session
            from mag.chat_source import agent_bio_id

            _materialize_session(sid, cwd)
            bio_id = agent_bio_id(_local_id(sid))
            st = pack_status(bio_id)
            summarize_session(
                bio_id,
                cwd=cwd,
                use_llm=True,
                force=not st.get("complete"),
                pdf=False,
                visual=False,
                amend=True,
                source="mag_agent",
            )
            if not pack_status(bio_id).get("complete"):
                summarize_session(
                    bio_id,
                    cwd=cwd,
                    use_llm=False,
                    force=True,
                    pdf=False,
                    visual=False,
                    amend=True,
                    source="mag_agent",
                )
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
