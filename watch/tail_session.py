#!/usr/bin/env python3
"""Tail the active Grok session into a local digest for the agent."""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import threading

AGENT_ROOT = Path(__file__).resolve().parents[1]


def _grok_home() -> Path:
    """Lazy ~/.grok resolution (Path.home() can raise in sandbox/service contexts)."""
    try:
        return Path.home() / ".grok"
    except (RuntimeError, OSError):
        return AGENT_ROOT.parent / ".grok"


GROK_HOME = _grok_home()
ACTIVE = GROK_HOME / "active_sessions.json"
SESSIONS = GROK_HOME / "sessions"
LIVE = AGENT_ROOT / "memory" / "live_from_grok.md"
DIGEST = AGENT_ROOT / "watch" / "session_digest.jsonl"
POINTER = AGENT_ROOT / "watch" / "active_session.json"
OFFSET = AGENT_ROOT / "watch" / ".chat_offset"
_WATCH_LOCK = threading.Lock()


def encode_cwd(cwd: str) -> str:
    return urllib.parse.quote(cwd, safe="")


def _find_chat(sid: str, cwd: str | None) -> Path | None:
    if cwd:
        p = SESSIONS / encode_cwd(cwd) / sid / "chat_history.jsonl"
        if p.is_file():
            return p
    if not SESSIONS.is_dir():
        return None
    for group in SESSIONS.iterdir():
        if not group.is_dir():
            continue
        cand = group / sid / "chat_history.jsonl"
        if cand.is_file():
            return cand
    return None


def resolve_session() -> tuple[str, Path] | None:
    if POINTER.is_file():
        try:
            meta = json.loads(POINTER.read_text(encoding="utf-8"))
            sid = meta.get("session_id")
            cwd = meta.get("cwd")
            if sid:
                p = _find_chat(sid, cwd)
                if p:
                    return sid, p
        except (json.JSONDecodeError, OSError):
            pass

    if not ACTIVE.is_file():
        return None
    try:
        data = json.loads(ACTIVE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not data:
        return None
    row = data[0] if isinstance(data, list) else data
    sid = row.get("session_id")
    cwd = row.get("cwd")
    if not sid:
        return None
    p = _find_chat(sid, cwd)
    if p:
        return sid, p
    return None


def load_offset() -> int:
    try:
        return int(OFFSET.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


def save_offset(n: int) -> None:
    OFFSET.parent.mkdir(parents=True, exist_ok=True)
    OFFSET.write_text(str(n), encoding="utf-8")


def summarize_line(obj: dict) -> dict:
    t = obj.get("type") or obj.get("role") or "msg"
    preview = ""
    if "content" in obj:
        c = obj["content"]
        if isinstance(c, str):
            preview = c
        elif isinstance(c, list):
            # extract text bits
            parts = []
            for item in c:
                if isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
                else:
                    parts.append(str(item))
            preview = " ".join(parts)
        else:
            preview = str(c)
    elif "summary" in obj:
        s = obj["summary"]
        if isinstance(s, list):
            preview = " ".join(
                str(x.get("text", x)) if isinstance(x, dict) else str(x) for x in s
            )
        else:
            preview = str(s)
    else:
        preview = json.dumps(obj, default=str)[:300]
    preview = preview.replace("\n", " ").strip()[:400]
    return {"type": str(t), "preview": preview}


def refresh_live(sid: str, recent: list[dict], source: str) -> None:
    LIVE.parent.mkdir(parents=True, exist_ok=True)
    bullets = "\n".join(
        f"- **{r['type']}:** {r['preview']}" for r in recent[-12:]
    ) or "- (waiting for messages)"
    LIVE.write_text(
        f"""# Live from Grok

- **updated:** {datetime.now(timezone.utc).isoformat()}
- **session:** `{sid}`
- **source:** `{source}`

## Recent turns (preview)

{bullets}

## How this works

Written by **Mag integral** (`python main.py lab` or `python main.py mag` — watch is baked in).
Optional standalone: `python main.py watch` only if Mag is not running.
If this file goes stale, the integral process was killed — restart `python main.py lab`.
Local only (T1) — do not send to free remote train-on-input APIs.
""",
        encoding="utf-8",
    )


def once() -> int:
    """Thread-safe single refresh of live board (integral Mag + optional CLI)."""
    with _WATCH_LOCK:
        return _once_unlocked()


def _once_unlocked() -> int:
    resolved = resolve_session()
    if not resolved:
        LIVE.parent.mkdir(parents=True, exist_ok=True)
        LIVE.write_text(
            "# Live from Grok\n\nNo active session found. Is Grok running?\n",
            encoding="utf-8",
        )
        print("no active session")
        return 1

    sid, path = resolved
    offset = load_offset()
    data = path.read_bytes()
    if offset > len(data):
        offset = 0
    chunk = data[offset:].decode("utf-8", errors="replace")
    new_lines = [ln for ln in chunk.splitlines() if ln.strip()]
    DIGEST.parent.mkdir(parents=True, exist_ok=True)
    recent: list[dict] = []
    with DIGEST.open("a", encoding="utf-8") as out:
        for ln in new_lines:
            try:
                obj = json.loads(ln)
            except json.JSONDecodeError:
                continue
            s = summarize_line(obj)
            s["ts"] = datetime.now(timezone.utc).isoformat()
            s["session_id"] = sid
            out.write(json.dumps(s) + "\n")
            recent.append(s)
    save_offset(len(data))

    if not recent:
        tail = path.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
        for ln in tail:
            try:
                recent.append(summarize_line(json.loads(ln)))
            except json.JSONDecodeError:
                pass

    refresh_live(sid, recent, str(path))
    POINTER.write_text(
        json.dumps(
            {
                "session_id": sid,
                "path": str(path),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"session={sid} new_lines={len(new_lines)} -> {LIVE}")
    return 0


def loop(interval: float = 3.0) -> None:
    print(f"Watching Grok -> {LIVE}")
    print("Ctrl+C to stop.")
    while True:
        once()
        time.sleep(interval)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=float, default=3.0)
    args = ap.parse_args()
    if args.once:
        return once()
    try:
        loop(args.interval)
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
