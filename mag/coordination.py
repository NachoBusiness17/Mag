"""Cross-seat coordination — shared activity + depth routing.

All seats (Cursor, DeepSeek, Grok TUI, local janitor) read the same activity
feed so agents see what others are doing. Depth classifier routes work to the
cheapest capable seat to preserve tokens ecosystem-wide.

Depths: overview | plan | heavy_code | simple_code | scut
Seats:  grok_tui (plan/overview) | deepseek (heavy) | local (simple/scut)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT, STATE_DIR

SCHEMA = "shared_activity.v1"
ACTIVITY_PATH = STATE_DIR / "shared_activity.jsonl"

VALID_DEPTHS = frozenset({"overview", "plan", "heavy_code", "simple_code", "scut"})

DEPTH_ROUTES: dict[str, dict[str, Any]] = {
    "overview": {
        "seat": "grok_tui",
        "mode": "plan",
        "launch": False,
        "tier": "L2-TUI",
        "token_hint": "File pack + ask in Grok TUI — do not auto-run remote.",
    },
    "plan": {
        "seat": "grok_tui",
        "mode": "plan",
        "launch": False,
        "tier": "L2-TUI",
        "token_hint": "Context-pack + [priority] Grok for architecture planning.",
    },
    "heavy_code": {
        "seat": "deepseek",
        "mode": "delegate",
        "launch": True,
        "provider": "deepseek",
        "tier": "L2-agent",
        "token_hint": "DeepSeek tool loop — multi-step coding.",
    },
    "simple_code": {
        "seat": "local",
        "mode": "dispatch",
        "launch": True,
        "provider": "ollama",
        "tier": "L0",
        "token_hint": "Local janitor / short dispatch — preserve remote tokens.",
    },
    "scut": {
        "seat": "local",
        "mode": "dispatch",
        "launch": True,
        "provider": "ollama",
        "tier": "L0",
        "token_hint": "Status, bonds, brief — never Grok.",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clip(s: str | None, n: int = 400) -> str:
    t = (s or "").replace("\r", " ").replace("\n", " ").strip()
    return t if len(t) <= n else t[: n - 1].strip() + "…"


def log_activity(
    *,
    seat: str,
    depth: str,
    goal: str,
    status: str = "running",
    actor: str | None = None,
    detail: str = "",
    task_id: str | None = None,
    activity_id: str | None = None,
) -> dict[str, Any]:
    """Append one row to state/shared_activity.jsonl (shared visibility)."""
    ACTIVITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": SCHEMA,
        "id": activity_id or f"act-{uuid.uuid4().hex[:12]}",
        "ts": _now(),
        "seat": (seat or "mag").strip() or "mag",
        "actor": (actor or seat or "mag").strip() or "mag",
        "depth": depth if depth in VALID_DEPTHS else "scut",
        "goal": _clip(goal, 500),
        "status": (status or "running").strip(),
        "detail": _clip(detail, 300),
        "task_id": task_id,
    }
    with ACTIVITY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def read_activity(*, limit: int = 40) -> list[dict[str, Any]]:
    if not ACTIVITY_PATH.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = ACTIVITY_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines[-max(1, min(limit, 200)) :]:
        if not line.strip():
            continue
        try:
            o = json.loads(line)
            if isinstance(o, dict):
                rows.append(o)
        except json.JSONDecodeError:
            continue
    rows.reverse()
    return rows


def activity_summary(*, limit: int = 12) -> dict[str, Any]:
    rows = read_activity(limit=limit)
    running = [r for r in rows if r.get("status") == "running"]
    by_seat: dict[str, int] = {}
    by_depth: dict[str, int] = {}
    for r in rows:
        s = str(r.get("seat") or "?")
        d = str(r.get("depth") or "?")
        by_seat[s] = by_seat.get(s, 0) + 1
        by_depth[d] = by_depth.get(d, 0) + 1
    path_str = str(ACTIVITY_PATH)
    try:
        if ACTIVITY_PATH.is_file():
            path_str = str(ACTIVITY_PATH.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        path_str = str(ACTIVITY_PATH)
    return {
        "ok": True,
        "schema": "coordination_summary.v1",
        "ts": _now(),
        "path": path_str,
        "running_n": len(running),
        "running": running[:8],
        "recent": rows[:limit],
        "by_seat": by_seat,
        "by_depth": by_depth,
    }


def format_activity_excerpt(*, limit: int = 6, max_chars: int = 900) -> str:
    """Plain block for context-pack injection."""
    rows = read_activity(limit=limit)
    if not rows:
        return ""
    lines = ["[COORDINATION — what other seats are doing]"]
    for r in rows[:limit]:
        lines.append(
            f"- {r.get('status', '?')} · {r.get('seat', '?')} · {r.get('depth', '?')} · "
            f"{r.get('goal', '')[:120]}"
        )
    text = "\n".join(lines)
    return text[:max_chars]


def classify_depth(goal: str, *, depth: str | None = None) -> dict[str, Any]:
    """Classify work depth and recommended seat (token-aware)."""
    if depth and depth in VALID_DEPTHS:
        route = dict(DEPTH_ROUTES[depth])
        return {
            "ok": True,
            "schema": "depth_class.v1",
            "depth": depth,
            "goal": _clip(goal, 300),
            "forced": True,
            **route,
        }

    g = (goal or "").lower()
    n = len(goal or "")

    if any(
        k in g
        for k in (
            "big picture",
            "interlink",
            "ecosystem map",
            "how does",
            "relate to",
            "overview",
            "two houses",
            "republic chain",
            "architecture map",
            "full stack",
        )
    ):
        depth = "overview"
    elif any(
        k in g
        for k in (
            "plan ",
            "design ",
            "tradeoff",
            "strategy",
            "roadmap",
            "architecture for",
            "how should we",
            "code planning",
        )
    ):
        depth = "plan"
    elif any(
        k in g
        for k in (
            "doctor",
            "health",
            "multi-smoke",
            "status",
            "what was i",
            "brief",
            "bonds",
            "list ",
            "show ",
            "ls ",
        )
    ) or (n < 80 and "?" in g):
        depth = "scut"
    elif any(
        k in g
        for k in (
            "rename",
            "typo",
            "one line",
            "single file",
            "add import",
            "fix lint",
            "small fix",
        )
    ) or (n < 120 and any(k in g for k in ("fix ", "patch ", "tweak "))):
        depth = "simple_code"
    elif any(
        k in g
        for k in (
            "implement",
            "refactor",
            "multi-file",
            "orchestrat",
            "write tests",
            "migrate",
            "build feature",
            "heavy",
            "tool loop",
        )
    ) or n > 350:
        depth = "heavy_code"
    elif any(k in g for k in ("implement", "refactor", "add ", "create ", "update ")):
        depth = "simple_code" if n < 200 else "heavy_code"
    else:
        depth = "simple_code" if n < 180 else "plan"

    route = dict(DEPTH_ROUTES[depth])
    return {
        "ok": True,
        "schema": "depth_class.v1",
        "depth": depth,
        "goal": _clip(goal, 300),
        "forced": False,
        **route,
    }


def coordinate(
    goal: str,
    *,
    depth: str | None = None,
    seat: str = "mag",
    actor: str | None = None,
    launch: bool = True,
    background: bool = False,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Classify depth, log activity, optionally launch the appropriate worker."""
    goal = (goal or "").strip()
    if not goal:
        return {"ok": False, "error": "empty goal"}

    classified = classify_depth(goal, depth=depth)
    d = str(classified["depth"])
    route = DEPTH_ROUTES[d]
    caller = (actor or seat or "mag").strip() or "mag"
    act = log_activity(
        seat=seat,
        depth=d,
        goal=goal,
        status="queued" if launch else "planned",
        actor=caller,
        detail=classified.get("token_hint") or "",
    )

    out: dict[str, Any] = {
        "ok": True,
        "schema": "coordinate.v1",
        "activity_id": act["id"],
        "classification": classified,
        "launched": False,
    }

    if not launch:
        out["action"] = "classified_only"
        return out

    if d in ("overview", "plan"):
        try:
            from mag.context_pack import build_context_pack, format_context_pack_text

            pack = build_context_pack(max_brief=700, max_live=300)
            text = format_context_pack_text(pack, max_chars=2400)
        except Exception as e:
            text = f"(pack failed: {e})"
        log_activity(
            seat="grok_tui",
            depth=d,
            goal=goal,
            status="planned",
            actor=caller,
            detail="Awaiting Grok TUI with context pack",
            activity_id=act["id"],
        )
        out.update(
            {
                "action": "file_for_grok",
                "seat": "grok_tui",
                "hint": classified.get("token_hint"),
                "pack_excerpt": text[:2400],
                "commands": {
                    "pack": "python main.py context-pack",
                    "grok": "Paste ACTIVATION + pack into Grok TUI with [priority]",
                },
            }
        )
        return out

    mode = route["mode"]
    if d == "heavy_code" and background:
        mode = "queue"

    log_activity(
        seat=route["seat"],
        depth=d,
        goal=goal,
        status="running",
        actor=caller,
        activity_id=act["id"],
    )

    try:
        if mode == "queue":
            from mag.orchestrator import enqueue

            task = enqueue(
                goal=goal,
                provider=route.get("provider") or "deepseek",
                tag=f"coord-{d}",
            )
            log_activity(
                seat=route["seat"],
                depth=d,
                goal=goal,
                status="queued",
                actor=caller,
                task_id=str(task.get("id") or task.get("task_id") or ""),
                detail="orchestrator queue",
                activity_id=act["id"],
            )
            out.update({"launched": True, "action": "queue", "mode": "queue", "task": task})
            return out

        if mode == "delegate":
            from mag.agent_cli import api_agent_turn

            sid = session_id or f"{seat}-coord"
            res = api_agent_turn(
                goal,
                provider=route.get("provider") or "deepseek",
                session_id=sid,
            )
            log_activity(
                seat=route["seat"],
                depth=d,
                goal=goal,
                status="done" if res.get("ok") else "failed",
                actor=caller,
                detail=_clip(str(res.get("error") or res.get("answer") or ""), 200),
                activity_id=act["id"],
            )
            out.update({"launched": True, "action": "delegate", "mode": "delegate", "result": res})
            return out

        if mode == "dispatch":
            from mag.dispatch import dispatch

            res = dispatch(goal, execute=True, force_seat=route.get("seat"))
            log_activity(
                seat=route.get("seat") or "local",
                depth=d,
                goal=goal,
                status="done" if res.get("ok", True) else "failed",
                actor=caller,
                detail=_clip(str(res.get("hint") or res.get("job") or ""), 200),
                activity_id=act["id"],
            )
            out.update({"launched": True, "action": "dispatch", "mode": "dispatch", "result": res})
            return out

    except Exception as e:
        log_activity(
            seat=route.get("seat") or seat,
            depth=d,
            goal=goal,
            status="failed",
            actor=caller,
            detail=str(e)[:200],
            activity_id=act["id"],
        )
        return {"ok": False, "error": str(e), "activity_id": act["id"], "classification": classified}

    return out
