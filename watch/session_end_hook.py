#!/usr/bin/env python3
"""Grok SessionEnd hook — Mag biographer summarizes the session.

Longer timeout than the light feed hook (Ollama may run).
Always exits 0 (fail-open).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_ROOT))

from mag.biography import summarize_session  # noqa: E402


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {}

    sid = (
        os.environ.get("GROK_SESSION_ID")
        or event.get("sessionId")
        or event.get("session_id")
    )
    cwd = event.get("cwd") or event.get("workspaceRoot") or os.environ.get("GROK_CWD")
    if not sid:
        # still try pointer
        ptr = AGENT_ROOT / "watch" / "active_session.json"
        if ptr.is_file():
            try:
                meta = json.loads(ptr.read_text(encoding="utf-8"))
                sid = meta.get("session_id")
                cwd = cwd or meta.get("cwd")
            except json.JSONDecodeError:
                pass
    if not sid:
        return 0

    # also log lightweight feed
    try:
        from watch.grok_hook import main as feed_main

        # re-feed with same stdin already consumed — write minimal record
        feed = AGENT_ROOT / "watch" / "grok_feed.jsonl"
        rec = {
            "hook_event": "session_end",
            "session_id": sid,
            "cwd": cwd,
        }
        with feed.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass

    try:
        from mag.biography import pack_status

        # Prefer full pack: force rewrite if artifacts missing even when chat mtime matches.
        st = pack_status(sid)
        force = not st.get("complete")
        # Lean DNA only — no PDF/visual on SessionEnd (export on demand via dashboard/API)
        result = summarize_session(
            sid, cwd=cwd, use_llm=True, force=force, pdf=False, visual=False, amend=True
        )
        # If LLM path left holes, one heuristic completion pass (no LLM)
        st2 = pack_status(sid)
        if not st2.get("complete"):
            result = summarize_session(
                sid,
                cwd=cwd,
                use_llm=False,
                force=True,
                pdf=False,
                visual=False,
                amend=True,
            )
            result["fallback_heuristic_complete"] = True
        logp = AGENT_ROOT / "logs" / "mag.jsonl"
        logp.parent.mkdir(parents=True, exist_ok=True)
        with logp.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "phase": "session_end_summary",
                        "pack_before": st,
                        "pack_after": pack_status(sid),
                        **result,
                    },
                    default=str,
                )
                + "\n"
            )
    except Exception as e:
        errp = AGENT_ROOT / "logs" / "biography_errors.log"
        errp.parent.mkdir(parents=True, exist_ok=True)
        with errp.open("a", encoding="utf-8") as f:
            f.write(f"{sid}: {e}\n")
        # last-ditch: heuristic only, still exit 0
        try:
            summarize_session(
                sid, cwd=cwd, use_llm=False, force=True, pdf=False, visual=False, amend=True
            )
        except Exception as e2:
            with errp.open("a", encoding="utf-8") as f:
                f.write(f"{sid} fallback: {e2}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
