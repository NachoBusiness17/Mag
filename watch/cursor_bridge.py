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
  python watch/cursor_bridge.py status
  python watch/cursor_bridge.py steer "goal" [--mode delegate|queue|handoff|dispatch]
  python watch/cursor_bridge.py handoff "FILE for Mag: …"
  python watch/cursor_bridge.py health
  python watch/cursor_bridge.py routes

The dashboard must be up (python main.py lab). For remote / cloud use:
  MAG_PUBLIC_URL=http://<home-tailscale>:8765
  MAG_REMOTE_TOKEN=<home-secret>
Cloud agents: run `status` first; if reachable, `steer` — do not bypass Mag.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Windows cp1252 stdout can't encode Unicode arrows/em-dashes in Mag text.
# Reconfigure stdout to UTF-8 with errors=replace so the bridge never crashes
# on a non-ASCII char in a context pack or agent reply.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = int(os.environ.get("MAG_BRIDGE_TIMEOUT", "120"))


def mag_url() -> str:
    """Home Mag base URL — cloud sets MAG_PUBLIC_URL; desktop may use MAG_URL."""
    return (
        os.environ.get("MAG_URL", "").strip()
        or os.environ.get("MAG_PUBLIC_URL", "").strip()
        or "http://127.0.0.1:8765"
    )


def _auth_headers() -> dict[str, str]:
    tok = os.environ.get("MAG_REMOTE_TOKEN", "").strip()
    if not tok:
        return {}
    return {"Authorization": f"Bearer {tok}"}


def _req(
    method: str,
    path: str,
    body: dict | None = None,
    timeout: int = TIMEOUT,
) -> tuple[int, dict[str, Any]]:
    url = mag_url().rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    headers: dict[str, str] = {}
    if data is not None:
        headers["Content-Type"] = "application/json"
    headers.update(_auth_headers())
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return r.status, json.loads(raw) if raw else {}


def _req_safe(
    method: str,
    path: str,
    body: dict | None = None,
    timeout: int = 5,
) -> tuple[int, dict[str, Any] | None, str | None]:
    try:
        status, data = _req(method, path, body=body, timeout=timeout)
        return status, data, None
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8", errors="replace") or "{}")
        except json.JSONDecodeError:
            payload = {"error": str(e)}
        return e.code, payload, str(e)
    except Exception as e:
        return 0, None, str(e)


def probe_hq() -> dict[str, Any]:
    """Can this seat reach Mag HQ? Used by cloud agents before steering."""
    base = mag_url()
    tok = bool(os.environ.get("MAG_REMOTE_TOKEN", "").strip())
    out: dict[str, Any] = {
        "reachable": False,
        "mag_url": base,
        "has_token": tok,
        "seat_hint": "cursor-cloud",
    }
    status, health, err = _req_safe("GET", "/api/v1/health", timeout=4)
    if err or not health:
        out["error"] = err or "health check failed"
        out["hint"] = (
            "Set MAG_PUBLIC_URL (+ MAG_REMOTE_TOKEN) in Cursor Cloud secrets; "
            "home must run launch_dashboard_lan.cmd or Tailscale."
        )
        return out
    out["health"] = health
    # Dashboard up = steerable (degraded = watch/mag not running; handoff/delegate still work)
    out["reachable"] = status == 200 and bool(health) and health.get("status") != "down"
    _, surface, _ = _req_safe("GET", "/api/v1/surface", timeout=4)
    if surface:
        out["surface"] = surface
    if out["reachable"]:
        out["hint"] = (
            "HQ up — steer with: python watch/cursor_bridge.py steer \"<goal>\" "
            "--mode delegate --provider deepseek --seat cursor-cloud"
        )
    return out


def cmd_status() -> int:
    st = probe_hq()
    print(json.dumps(st, indent=2, default=str))
    return 0 if st.get("reachable") else 2


def cmd_handoff(text: str, source: str, device: str, kind: str) -> int:
    body: dict[str, Any] = {
        "text": text,
        "source": source or "cursor-cloud",
        "device": device or "cursor-bridge",
    }
    if kind:
        body["kind"] = kind
    status, data, err = _req_safe("POST", "/api/v1/handoff/file", body=body, timeout=TIMEOUT)
    if err or status != 200:
        print(
            json.dumps({"ok": False, "status": status, "error": err, "data": data}, indent=2),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(data, indent=2, default=str)[:8000])
    return 0 if data.get("ok", True) else 1


def cmd_steer(
    goal: str,
    *,
    mode: str,
    seat: str,
    provider: str,
    pack: bool,
    background: bool,
) -> int:
    """Steering seat: probe HQ → optional pack → delegate/queue/handoff on home Mag."""
    probe = probe_hq()
    if not probe.get("reachable"):
        payload = {
            "steered": False,
            "probe": probe,
            "fallback": "clone_or_handoff_when_home_up",
            "goal": goal,
            "hint": (
                "HQ unreachable from this VM — enqueue on home when up, or minimal clone PR. "
                "Do not pretend Mag does not exist; wire MAG_PUBLIC_URL."
            ),
        }
        print(json.dumps(payload, indent=2, default=str))
        return 2

    context_snippet = ""
    if pack:
        _, pack_data, _ = _req_safe("GET", "/api/v1/context-pack", timeout=TIMEOUT)
        if pack_data and pack_data.get("ok"):
            context_snippet = (pack_data.get("text") or pack_data.get("paste") or "")[:4000]

    routed_mode = mode
    if routed_mode == "auto":
        routed_mode = "queue" if background else "delegate"

    if routed_mode == "handoff":
        text = goal if "file for mag" in goal.lower() else (
            f"FILE for Mag:\n- turned: cloud steer enqueue\n"
            f"- open loops: …\n- next move: {goal[:500]}"
        )
        status, data, err = _req_safe(
            "POST",
            "/api/v1/handoff/file",
            body={
                "text": text,
                "source": seat,
                "device": "cursor-bridge-steer",
                "kind": "auto",
            },
            timeout=TIMEOUT,
        )
        rc = 0 if status == 200 and (data or {}).get("ok", True) else 1
        result = {
            "steered": rc == 0,
            "mode": "handoff",
            "goal": goal,
            "handoff": data,
            "error": err,
        }
    else:
        body: dict[str, Any] = {
            "mode": routed_mode,
            "seat": seat,
            "goal": goal,
            "provider": provider,
            "tag": f"{seat}-steered",
            "session_id": seat,
        }
        status, data, err = _req_safe("POST", "/api/v1/seat/task", body=body, timeout=TIMEOUT)
        rc = 0 if status == 200 and (data or {}).get("ok", True) else 1
        result = {
            "steered": rc == 0,
            "mode": routed_mode,
            "goal": goal,
            "provider": provider,
            "task": data,
            "error": err,
        }

    print(
        json.dumps(
            {"probe": {"reachable": True, "mag_url": probe.get("mag_url")}, **result},
            indent=2,
            default=str,
        )
    )
    if context_snippet:
        print("\n--- context pack (head) ---\n", context_snippet[:3000], sep="", file=sys.stderr)
    return rc


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


def cmd_register(goal: str, seat: str, mode: str) -> int:
    """Register this Cursor session with orchestrator mesh (MAG_TASK_ID for steer/reap)."""
    status, data = _req("POST", "/api/v1/seats/register", {
        "seat": seat,
        "goal": goal or "Cursor session",
        "mode": mode,
        "parent": "cursor_bridge",
    })
    if status != 200 or not data.get("ok", True):
        print(f"[cursor_bridge] register failed ({status}): {data}", file=sys.stderr)
        return 1
    tid = data.get("task_id") or data.get("mag_task_id")
    print(json.dumps(data, indent=2, default=str)[:4000])
    if tid:
        print(f"\nMAG_TASK_ID={tid}", file=sys.stderr)
    return 0


def cmd_improve(claim: str, goal: str, brief: str, enqueue: bool, drain: bool) -> int:
    """File cloud/desktop improve claim → behavioral + nervous + spider + optional queue."""
    body: dict = {
        "claim": claim,
        "goal": goal or (f"[improve] {claim}" if claim else ""),
        "brief": brief,
        "source": "cursor-bridge",
        "enqueue": enqueue or drain,
    }
    if drain:
        status, data = _req("POST", "/api/v1/improve/cycle", {
            "source": "cursor-bridge",
            "drain": True,
            "max_improve": 2,
        })
    else:
        status, data = _req("POST", "/api/v1/improve/cloud", body)
    if status not in (200, 422) or not data.get("ok", True):
        print(f"[cursor_bridge] improve failed ({status}): {data}", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, default=str)[:8000])
    return 0


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

    p_reg = sub.add_parser("register", help="register Cursor session with orchestrator mesh")
    p_reg.add_argument("goal", nargs="?", default="Cursor session", help="session goal label")
    p_reg.add_argument("--seat", default="cursor")
    p_reg.add_argument("--mode", default="interactive", choices=("interactive", "cloud", "oneshot"))
    p_reg.set_defaults(cmd="register")

    p_imp = sub.add_parser("improve", help="file improve claim → behavioral + queue + spider")
    p_imp.add_argument("--claim", default="", help="concrete improve claim")
    p_imp.add_argument("--goal", default="", help="full goal (default: [improve] claim)")
    p_imp.add_argument("--brief", default="", help="optional brief for handoff file")
    p_imp.add_argument("--enqueue", action="store_true", help="file handoff + run improve cycle")
    p_imp.add_argument("--drain", action="store_true", help="run improve cycle + drain one task")
    p_imp.set_defaults(cmd="improve")

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

    p_status = sub.add_parser("status", help="probe Mag HQ reachability (cloud: run first)")
    p_status.set_defaults(cmd="status")

    p_ho = sub.add_parser("handoff", help="POST FILE/goal to home queue/working")
    p_ho.add_argument("text", help="goal text or FILE block")
    p_ho.add_argument("--source", default="cursor-cloud")
    p_ho.add_argument("--device", default="cursor-bridge")
    p_ho.add_argument("--kind", default="", choices=("", "todo", "file", "auto"))
    p_ho.set_defaults(cmd="handoff")

    p_steer = sub.add_parser(
        "steer",
        help="steering seat: probe → pack → delegate DeepSeek / queue / handoff on home",
    )
    p_steer.add_argument("goal", help="goal to route to home Mag")
    p_steer.add_argument(
        "--mode",
        default="auto",
        choices=("auto", "delegate", "queue", "handoff", "dispatch", "agent"),
    )
    p_steer.add_argument("--seat", default="cursor-cloud")
    p_steer.add_argument("--provider", default="deepseek")
    p_steer.add_argument("--pack", action="store_true", help="include context-pack head on stderr")
    p_steer.add_argument("--background", action="store_true", help="auto mode → queue")
    p_steer.set_defaults(cmd="steer")

    args = ap.parse_args()
    if args.cmd == "ask":
        return cmd_ask(args.goal, args.session, args.provider, args.model, args.reset)
    if args.cmd == "queue":
        return cmd_queue(args.goal, args.provider, args.tag)
    if args.cmd == "autopilot":
        return cmd_autopilot(args.drain)
    if args.cmd == "register":
        return cmd_register(args.goal, args.seat, args.mode)
    if args.cmd == "improve":
        if not args.claim and not args.goal and not args.drain:
            print("[cursor_bridge] improve needs --claim or --goal or --drain", file=sys.stderr)
            return 1
        return cmd_improve(args.claim, args.goal, args.brief, args.enqueue, args.drain)
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
    if args.cmd == "status":
        return cmd_status()
    if args.cmd == "handoff":
        return cmd_handoff(args.text, args.source, args.device, args.kind)
    if args.cmd == "steer":
        return cmd_steer(
            args.goal,
            mode=args.mode,
            seat=args.seat,
            provider=args.provider,
            pack=bool(args.pack),
            background=bool(args.background),
        )
    return args.fn()


if __name__ == "__main__":
    sys.exit(main())
