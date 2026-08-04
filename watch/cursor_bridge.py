#!/usr/bin/env python3
"""Cursor <-> Mag REST bridge client.

Cursor (L2-Cursor seat) talks to Mag's dashboard REST API (:8765) to:
  * pull the current context pack  -> GET  /api/v1/context-pack
  * run a tool-using Mag agent turn -> POST /api/v1/agent
  * unified seat tasking            -> POST /api/v1/seat/task
  * read health / nervous status    -> GET  /api/v1/health
  * enqueue orchestrator goal       -> POST /api/v1/orchestrator/queue
  * autopilot (improve + governor)  -> POST /api/v1/autopilot

Usage (from Cursor terminal or a hook):
  python watch/cursor_bridge.py pack
  python watch/cursor_bridge.py ask "goal text" [--session cursor-xyz] [--provider deepseek]
  python watch/cursor_bridge.py delegate "tool-heavy goal"
  python watch/cursor_bridge.py queue "background goal"
  python watch/cursor_bridge.py task "goal" --mode delegate|queue|agent|dispatch
  python watch/cursor_bridge.py activity [--limit 20]
  python watch/cursor_bridge.py coordinate "goal" [--dry] [--background] [--depth heavy_code]
  python watch/cursor_bridge.py autopilot [--drain]
  python watch/cursor_bridge.py health
  python watch/cursor_bridge.py routes

The dashboard must be up (python main.py lab). For remote use, point MAG_URL
at the remote host (e.g. http://mag-box:8765) and tunnel if needed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

# Windows cp1252 stdout can't encode Unicode arrows/em-dashes in Mag text.
# Reconfigure stdout to UTF-8 with errors=replace so the bridge never crashes
# on a non-ASCII char in a context pack or agent reply.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = os.environ.get("MAG_URL", "http://127.0.0.1:8765")
TIMEOUT = int(os.environ.get("MAG_BRIDGE_TIMEOUT", "120"))


def _req(method: str, path: str, body: dict | None = None, timeout: int = TIMEOUT):
    url = DEFAULT_URL.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read())


def cmd_pack() -> int:
    """Fetch and print the current context pack text."""
    status, data = _req("GET", "/api/v1/context-pack")
    if status != 200 or not data.get("ok"):
        print(f"[cursor_bridge] context-pack failed: {data}", file=sys.stderr)
        return 1
    print(data.get("text") or data.get("paste") or "(empty)")
    return 0


def cmd_ask(goal: str, session: str, provider: str, model: str | None, reset: bool) -> int:
    """Run a tool-using Mag agent turn and print the result."""
    body = {
        "goal": goal,
        "session_id": session,
        "provider": provider,
        "reset": reset,
    }
    if model:
        body["model"] = model
    status, data = _req("POST", "/api/v1/agent", body)
    if status != 200:
        print(f"[cursor_bridge] agent turn failed ({status}): {data}", file=sys.stderr)
        return 1
    # Print a compact summary of the turn result.
    print(json.dumps(data, indent=2, default=str)[:8000])
    return 0


def cmd_health() -> int:
    status, data = _req("GET", "/api/v1/health")
    print(json.dumps(data, indent=2, default=str)[:4000])
    return 0


def cmd_routes() -> int:
    status, data = _req("GET", "/api/v1")
    print(json.dumps(data, indent=2, default=str)[:4000])
    return 0


def cmd_queue(goal: str, provider: str, tag: str) -> int:
    status, data = _req("POST", "/api/v1/orchestrator/queue", {
        "goal": goal,
        "provider": provider,
        "tag": tag or "cursor-queued",
    })
    print(json.dumps(data, indent=2, default=str)[:4000])
    return 0 if data.get("ok") else 1


def cmd_autopilot(drain: bool) -> int:
    status, data = _req("POST", "/api/v1/autopilot", {
        "queue_improve": True,
        "governor": True,
        "drain": drain,
    })
    print(json.dumps(data, indent=2, default=str)[:8000])
    return 0 if data.get("ok") else 1


def cmd_delegate(goal: str, session: str, provider: str) -> int:
    """Heavy tool work through Mag's loop — use from Cursor when edits need Mag tools."""
    print(f"[cursor_bridge] delegating to Mag agent ({provider})…", file=sys.stderr)
    return cmd_ask(goal, session, provider, None, False)


def cmd_task(
    goal: str | None,
    mode: str,
    seat: str,
    session: str,
    provider: str,
    tag: str,
    drain: bool,
) -> int:
    """Unified seat task — preferred entry for Cursor→Mag handoffs."""
    body: dict = {"mode": mode, "seat": seat}
    if goal:
        body["goal"] = goal
    if provider:
        body["provider"] = provider
    if tag:
        body["tag"] = tag
    if session and session != seat:
        body["session_id"] = session
    if mode == "autopilot":
        body["drain"] = drain
    status, data = _req("POST", "/api/v1/seat/task", body)
    if status != 200 or not data.get("ok", True):
        print(f"[cursor_bridge] seat/task failed ({status}): {data}", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, default=str)[:8000])
    return 0


def cmd_activity(limit: int = 20) -> int:
    """Shared activity feed — what all seats are doing."""
    status, data = _req("GET", f"/api/v1/coordination?limit={max(1, min(limit, 80))}")
    if status != 200:
        print(f"[cursor_bridge] coordination failed ({status}): {data}", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, default=str)[:8000])
    return 0


def cmd_coordinate(
    goal: str,
    *,
    depth: str | None,
    seat: str,
    dry: bool,
    background: bool,
) -> int:
    """Depth classify + launch (token-aware routing)."""
    body: dict = {
        "goal": goal,
        "seat": seat,
        "launch": not dry,
        "background": background,
    }
    if depth:
        body["depth"] = depth
    status, data = _req("POST", "/api/v1/coordinate", body)
    if status != 200 or not data.get("ok", True):
        print(f"[cursor_bridge] coordinate failed ({status}): {data}", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, default=str)[:8000])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Cursor <-> Mag REST bridge")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_pack = sub.add_parser("pack", help="fetch context pack")
    p_pack.set_defaults(fn=cmd_pack)

    p_ask = sub.add_parser("ask", help="run a Mag agent turn")
    p_ask.add_argument("goal", help="goal / prompt for the agent")
    p_ask.add_argument("--session", default="cursor", help="session id")
    p_ask.add_argument("--provider", default="deepseek", help="provider (deepseek|ollama)")
    p_ask.add_argument("--model", default=None, help="model override")
    p_ask.add_argument("--reset", action="store_true", help="reset session first")
    p_ask.set_defaults(fn=cmd_ask)

    p_health = sub.add_parser("health", help="Mag health")
    p_health.set_defaults(fn=cmd_health)

    p_routes = sub.add_parser("routes", help="list dashboard API routes")
    p_routes.set_defaults(fn=cmd_routes)

    p_q = sub.add_parser("queue", help="enqueue orchestrator goal")
    p_q.add_argument("goal", help="goal text")
    p_q.add_argument("--provider", default="deepseek")
    p_q.add_argument("--tag", default="cursor")
    p_q.set_defaults(cmd="queue")

    p_ap = sub.add_parser("autopilot", help="improve queue + governor + seed status")
    p_ap.add_argument("--drain", action="store_true")
    p_ap.set_defaults(cmd="autopilot")

    p_del = sub.add_parser("delegate", help="Mag agent turn for tool-heavy work")
    p_del.add_argument("goal", help="goal")
    p_del.add_argument("--session", default="cursor")
    p_del.add_argument("--provider", default="deepseek")
    p_del.set_defaults(cmd="delegate")

    p_task = sub.add_parser("task", help="unified seat task (preferred)")
    p_task.add_argument("goal", nargs="?", default=None, help="goal (omit for autopilot)")
    p_task.add_argument(
        "--mode",
        default="delegate",
        choices=("delegate", "queue", "autopilot", "agent", "dispatch"),
        help="task mode",
    )
    p_task.add_argument("--seat", default="cursor", help="calling seat id")
    p_task.add_argument("--session", default=None, help="agent session (defaults to seat)")
    p_task.add_argument("--provider", default="deepseek")
    p_task.add_argument("--tag", default=None, help="orchestrator queue tag")
    p_task.add_argument("--drain", action="store_true", help="autopilot: drain queue after")
    p_task.set_defaults(cmd="task")

    p_act = sub.add_parser("activity", help="shared seat activity feed")
    p_act.add_argument("--limit", type=int, default=20)
    p_act.set_defaults(cmd="activity")

    p_coord = sub.add_parser("coordinate", help="depth classify + launch (token-aware)")
    p_coord.add_argument("goal", help="goal text")
    p_coord.add_argument(
        "--depth",
        default="",
        choices=("overview", "plan", "heavy_code", "simple_code", "scut", ""),
    )
    p_coord.add_argument("--seat", default="cursor")
    p_coord.add_argument("--dry", action="store_true", help="classify only")
    p_coord.add_argument("--background", action="store_true", help="queue heavy work")
    p_coord.set_defaults(cmd="coordinate")

    args = ap.parse_args()
    if args.cmd == "ask":
        return cmd_ask(args.goal, args.session, args.provider, args.model, args.reset)
    if args.cmd == "queue":
        return cmd_queue(args.goal, args.provider, args.tag)
    if args.cmd == "autopilot":
        return cmd_autopilot(args.drain)
    if args.cmd == "delegate":
        return cmd_delegate(args.goal, args.session, args.provider)
    if args.cmd == "task":
        session = args.session or args.seat
        tag = args.tag or f"{args.seat}-queued"
        if args.mode != "autopilot" and not args.goal:
            print("[cursor_bridge] goal required unless --mode autopilot", file=sys.stderr)
            return 1
        return cmd_task(
            args.goal,
            args.mode,
            args.seat,
            session,
            args.provider,
            tag,
            args.drain,
        )
    if args.cmd == "activity":
        return cmd_activity(args.limit)
    if args.cmd == "coordinate":
        return cmd_coordinate(
            args.goal,
            depth=(args.depth or None),
            seat=args.seat,
            dry=bool(args.dry),
            background=bool(args.background),
        )
    return args.fn()


if __name__ == "__main__":
    sys.exit(main())
