"""Intelligent governor autorun — fill queue, plan, route, execute.

The drainer (MAG_DRAINER=1) runs this loop instead of blind orchestrator drain:

  1. **Fill** — improve candidates, agent_state next_moves, handoff JSON → queue
  2. **Plan** — classify depth, match skills, estimate cost, pick provider/rental
  3. **Execute** — orchestrator drain for queued work, else governor cycle

Routing uses coordination.depth + models.quota.pick_provider (budget-aware),
configs/skills.yaml + IJL skill beads, and vast rental when configured.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TRAIL = ROOT / "memory" / "runs" / "governor_autorun_trail.jsonl"

from mag.router import DEPTH_JOB_MAP  # single law — ponytail: no duplicate maps

DEPTH_COST_MULT: dict[str, int] = {
    "scut": 1,
    "simple_code": 2,
    "heavy_code": 8,
    "plan": 3,
    "overview": 2,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_trail(entry: dict[str, Any]) -> None:
    TRAIL.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": _now(), **entry}
    with TRAIL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    try:
        from mag.training_events import emit

        phase = str(entry.get("phase") or "autorun")
        emit(
            "autorun_cycle",
            input_data={"phase": phase, "keys": list(entry.keys())[:12]},
            action={k: entry[k] for k in ("phase", "goal", "tag") if k in entry},
            outcome={"logged": True},
            pattern_tags=[f"gov_{phase}"],
        )
    except Exception:
        pass


def _drainer_active() -> bool:
    if os.environ.get("MAG_DRAINER", "").strip().lower() in ("1", "true", "yes"):
        return True
    try:
        from mag.preferences import drainer_enabled

        return drainer_enabled()
    except Exception:
        return False


def estimate_cost(goal: str, depth: str, provider: str) -> dict[str, Any]:
    """Rough token projection for routing decisions (not billing)."""
    base = max(500, len(goal or "") * 4)
    mult = DEPTH_COST_MULT.get(depth, 2)
    tokens = base * mult
    return {
        "tokens_est": tokens,
        "depth": depth,
        "provider": provider,
        "tier_hint": "L0" if provider == "ollama" else "L2",
    }


def match_skills(goal: str, depth: str, job: str) -> list[str]:
    """Connected skills from configs/skills.yaml + IJL beads."""
    skills: list[str] = []
    try:
        from mag.skills_pack import load_skills_cfg

        cfg = load_skills_cfg()
        job_map = cfg.get("job_to_skills") or {}
        skills.extend(list(job_map.get(job) or job_map.get("default") or []))
    except Exception:
        pass
    try:
        from ijl_core import skill_excerpt_for_goal

        if skill_excerpt_for_goal(goal, max_chars=40).strip():
            skills.append("ijl:matched")
    except Exception:
        pass
    # depth-specific skill hints from configs when tags overlap
    if depth in ("heavy_code", "simple_code") and "patch-verify" not in skills:
        g = (goal or "").lower()
        if any(k in g for k in ("fix", "patch", "refactor", "implement")):
            skills.append("patch-verify")
    return skills


def route_task(goal: str, *, depth: str | None = None) -> dict[str, Any]:
    """Plan one goal: depth, provider, mode, projected cost, skills (unified router)."""
    try:
        from mag.router import route as unified_route

        r = unified_route(goal, depth=depth)
        d = str(r.get("depth") or "simple_code")
        provider = str(r.get("provider") or "ollama")
        cost = estimate_cost(goal, d, provider)
        return {
            "ok": bool(r.get("ok", True)),
            "schema": "route.v2",
            "goal": (goal or "")[:300],
            "depth": d,
            "job": str(r.get("job") or DEPTH_JOB_MAP.get(d, "default")),
            "provider": provider,
            "mode": str(r.get("mode") or "dispatch"),
            "launch": bool(r.get("launch", True)),
            "executable": bool(r.get("executable", True)),
            "rental": bool(r.get("rental")),
            "classification": r.get("classified") or {},
            "pick": r.get("pick") or {},
            "cost_estimate": cost,
            "skills": list(r.get("skills") or match_skills(goal, d, str(r.get("job") or ""))),
            "hint": str(r.get("hint") or "")[:200],
            "error": r.get("error"),
        }
    except Exception:
        pass

    from mag.coordination import classify_depth
    from models.quota import pick_provider, provider_budget

    classified = classify_depth(goal, depth=depth)
    d = str(classified.get("depth") or "simple_code")
    job = DEPTH_JOB_MAP.get(d, "default")

    prefer: list[str] | None = None
    rental = False
    if d == "heavy_code":
        vast = provider_budget("vast")
        if vast.get("configured") and vast.get("budget_ok"):
            prefer = ["vast", "deepseek", "deepseek_overmind", "anthropic", "ollama"]
            rental = True
    elif d in ("scut", "simple_code"):
        prefer = ["ollama", "groq", "openrouter", "deepseek"]

    picked = pick_provider(job=job, prefer=prefer)
    provider = picked.get("provider") or classified.get("provider") or "ollama"
    if not picked.get("ok") and d in ("scut", "simple_code"):
        provider = "ollama"

    cost = estimate_cost(goal, d, provider)
    skills = match_skills(goal, d, job)

    return {
        "ok": True,
        "schema": "route.v1",
        "goal": (goal or "")[:300],
        "depth": d,
        "job": job,
        "provider": provider,
        "mode": classified.get("mode") or "dispatch",
        "launch": bool(classified.get("launch", True)),
        "rental": rental,
        "classification": classified,
        "pick": picked,
        "cost_estimate": cost,
        "skills": skills,
    }


def _todo_has_text(text: str) -> bool:
    todo = ROOT / "queue" / "todo.md"
    if not todo.is_file():
        return False
    needle = text.strip()[:80]
    for line in todo.read_text(encoding="utf-8", errors="replace").splitlines():
        if needle and needle in line:
            return True
    return False


def _append_todo_mag(text: str) -> bool:
    if _todo_has_text(text):
        return False
    todo = ROOT / "queue" / "todo.md"
    todo.parent.mkdir(parents=True, exist_ok=True)
    if not todo.is_file():
        todo.write_text("# Todo\n\n", encoding="utf-8")
    with todo.open("a", encoding="utf-8") as f:
        f.write(f"- [ ] [mag] {text.strip()}\n")
    return True


def queue_has_goal(goal: str) -> bool:
    from mag.orchestrator import list_queue

    g = (goal or "").strip()
    for q in list_queue(limit=80):
        if (q.get("goal") or "").strip() == g and q.get("status") in ("queued", "running"):
            return True
    return False


def enqueue_routed(goal: str, *, tag: str = "", depth: str | None = None) -> dict[str, Any]:
    """Enqueue with governor routing (provider + depth metadata)."""
    from mag.autorun_common import fkb_block_for_goal, refresh_context_for_goal
    from mag.orchestrator import enqueue

    goal = goal.strip()
    block = fkb_block_for_goal(goal)
    if block:
        return {"ok": False, "error": block, "goal": goal[:120]}

    route = route_task(goal, depth=depth)
    if route.get("depth") in ("overview", "plan"):
        return {
            "ok": False,
            "error": "plan_depth_not_queued",
            "goal": goal[:120],
            "route": route,
            "hint": route.get("hint") or "Use context-pack + Grok TUI for plan depth",
        }
    if route.get("executable") is False:
        return {
            "ok": False,
            "error": route.get("error") or "not_executable",
            "goal": goal[:120],
            "route": route,
            "hint": route.get("hint"),
        }

    refresh_context_for_goal(goal)
    if "[improve]" in goal.lower():
        try:
            from mag.conductor import conduct

            conduct(goal, dry=False)
        except Exception:
            pass
    rec = enqueue(
        goal,
        provider=str(route.get("provider") or "deepseek"),
        tag=tag or f"route-{route.get('depth', 'job')}",
    )
    rec["route"] = route
    return rec


def fill_queue(
    *,
    max_improve: int = 2,
    max_state: int = 2,
    max_handoff: int = 2,
    max_verkle: int = 2,
) -> dict[str, Any]:
    """Intelligently seed orchestrator queue + todo from real sources."""
    filled: dict[str, Any] = {
        "improve": [],
        "agent_state": [],
        "handoff": [],
        "verkle": [],
        "skipped": [],
    }

    try:
        from mag.autopilot import _top_improve_candidates

        for cand in _top_improve_candidates(max_improve):
            claim = str(cand.get("claim") or cand.get("id") or "")[:300]
            if not claim:
                continue
            goal = f"[improve] {claim}"
            if queue_has_goal(goal):
                filled["skipped"].append(goal[:60])
                continue
            rec = enqueue_routed(goal, tag=f"improve-{str(cand.get('id', ''))[:12]}")
            filled["improve"].append(rec)
    except Exception as e:
        filled["improve_error"] = str(e)

    try:
        from mag.agent_state import load_latest

        st = load_latest()
        if st:
            for m in (st.get("next_moves") or [])[:max_state]:
                if isinstance(m, dict):
                    status = str(m.get("status") or "open")
                    text = str(m.get("title") or m.get("text") or m.get("move") or "")
                else:
                    status, text = "open", str(m)
                if status == "deferred" or not text.strip():
                    continue
                goal = text.strip()
                if queue_has_goal(goal) and _todo_has_text(goal):
                    filled["skipped"].append(goal[:60])
                    continue
                _append_todo_mag(goal)
                if not queue_has_goal(goal):
                    rec = enqueue_routed(goal, tag="agent-state")
                    filled["agent_state"].append(rec)
    except Exception as e:
        filled["agent_state_error"] = str(e)

    handoff_dir = ROOT / "queue" / "handoff"
    if handoff_dir.is_dir():
        for p in sorted(handoff_dir.glob("*.json"))[:max_handoff]:
            try:
                h = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            goal = str(h.get("goal") or h.get("brief") or h.get("title") or "").strip()
            if not goal or queue_has_goal(goal):
                continue
            rec = enqueue_routed(goal, tag=f"handoff-{p.stem[:12]}", depth=h.get("depth"))
            filled["handoff"].append({**rec, "handoff_file": p.name})

    try:
        from mag.verkle_audit import verkle_gaps

        for gap in verkle_gaps():
            if len(filled["verkle"]) >= max_verkle:
                break
            if gap.get("severity") not in ("warn", "error"):
                continue
            act = str(gap.get("action") or "").strip()
            detail = str(gap.get("detail") or "")[:200]
            if not act:
                continue
            goal = f"[verkle] {detail} — run: {act}"
            if queue_has_goal(goal):
                filled["skipped"].append(goal[:60])
                continue
            rec = enqueue_routed(goal, tag="verkle-gap", depth="scut")
            filled["verkle"].append({**rec, "gap": gap})
    except Exception as e:
        filled["verkle_error"] = str(e)

    filled["total_queued"] = (
        len(filled["improve"])
        + len(filled["agent_state"])
        + len(filled["handoff"])
        + len(filled["verkle"])
    )
    _log_trail(
        {
            "phase": "fill",
            **{
                k: filled[k]
                for k in ("improve", "agent_state", "handoff", "verkle", "total_queued", "skipped")
            },
        }
    )
    return filled


def plan_pending() -> dict[str, Any]:
    """Annotate pending work with routes (cost, skills, provider)."""
    from mag.governor import queue_candidates
    from mag.orchestrator import list_queue, queue_status

    orch_plans: list[dict[str, Any]] = []
    for q in list_queue(limit=30):
        if q.get("status") != "queued":
            continue
        goal = str(q.get("goal") or "")
        orch_plans.append(
            {
                "queue_id": q.get("queue_id"),
                "goal": goal[:120],
                "route": route_task(goal),
            }
        )

    todo_plans: list[dict[str, Any]] = []
    for c in queue_candidates():
        todo_plans.append(
            {
                "title": str(c.get("title") or "")[:120],
                "route": route_task(str(c.get("title") or "")),
            }
        )

    plan = {
        "schema": "autorun_plan.v1",
        "ts": _now(),
        "orchestrator_queued": orch_plans,
        "todo_mag": todo_plans,
        "queue_status": queue_status(),
    }
    _log_trail({"phase": "plan", "queued_n": len(orch_plans), "todo_n": len(todo_plans)})
    return plan


def _seat_failed(out: str, rc: int) -> bool:
    if rc != 0:
        return True
    if "Stopped:" in out:
        return True
    if "**Agent error:**" in out:
        return True
    return False


def _seat_dispatch_with_fallback(text: str, provider: str) -> tuple[bool, str]:
    """Subprocess seat dispatch with guard-stop / agent-error fallback."""
    import mag.governor as gov

    fallback = gov.FALLBACK_PROVIDER
    providers_tried: list[str] = []
    rc, out, tail = 0, "", ""
    for prov in (provider, fallback, gov.PRIMARY_PROVIDER):
        if prov in providers_tried:
            continue
        providers_tried.append(prov)
        rc, out, tail = gov._run_seat(text, prov)
        if rc != 0:
            break  # seat-internal crash — provider swap cannot help
        if "Stopped:" in out or "**Agent error:**" in out:
            continue  # reliability signal — try next provider
        break
    if rc != 0:
        used = providers_tried[-1] if providers_tried else provider
        return False, f"seat {used} exit={rc}: {tail}"
    if "Stopped:" in out or "**Agent error:**" in out:
        return False, (
            f"seat guard-stop on {' AND '.join(providers_tried)} (NOT marked done): {tail}"
        )
    used = providers_tried[-1] if providers_tried else provider
    if len(providers_tried) > 1 and used == fallback:
        return True, f"fallback {fallback} exit=0: {tail}"
    return True, f"seat {used} exit=0: {tail}"


def execute_routed_task(text: str, *, who: str = "mag") -> tuple[bool, str]:
    """Governor executor: route then run through coordination network or seat."""
    import mag.governor as gov

    if who != "mag":
        return False, "not assigned to mag - skipping"

    route = route_task(text)
    depth = route["depth"]
    provider = route["provider"]

    if depth in ("overview", "plan"):
        from mag.coordination import coordinate

        res = coordinate(text, depth=depth, launch=False)
        hint = str(res.get("hint") or res.get("action") or "file_for_grok")
        return False, f"planned ({depth}): {hint[:180]}"

    if depth == "heavy_code" and _drainer_active():
        if not queue_has_goal(text):
            enqueue_routed(text, tag=f"gov-{depth}")
        return False, f"queued on orchestrator ({provider})"

    from mag.coordination import coordinate

    try:
        res = coordinate(
            text,
            depth=depth,
            seat="governor",
            actor="governor",
            launch=True,
            background=(depth == "heavy_code"),
        )
    except Exception as e:
        ok, detail = _seat_dispatch_with_fallback(text, provider)
        if ok:
            gov._mark_queue_done(text)
        return ok, f"coordinate error, seat fallback: {detail}"[:300]

    if not res.get("ok"):
        ok, detail = _seat_dispatch_with_fallback(text, provider)
        if ok:
            gov._mark_queue_done(text)
        return ok, detail

    action = str(res.get("action") or "")
    if action == "file_for_grok":
        return False, f"planned: needs Grok TUI ({depth})"

    if action == "queue":
        return False, f"queued: {str((res.get('task') or {}).get('queue_id') or '?')}"

    if action in ("delegate", "dispatch"):
        result = res.get("result") or {}
        err = str(result.get("error") or "")
        ans = str(result.get("answer") or result.get("text") or "")
        if err or "**Agent error:**" in ans or result.get("ok") is False:
            ok, detail = _seat_dispatch_with_fallback(text, provider)
            if ok:
                gov._mark_queue_done(text)
            return ok, f"{action} failed, seat: {detail}"[:300]
        gov._mark_queue_done(text)
        detail = (ans or str(result.get("hint") or result.get("job") or ""))[:200]
        return True, f"{action} ok: {detail}"

    ok, detail = _seat_dispatch_with_fallback(text, provider)
    if ok:
        gov._mark_queue_done(text)
    return ok, detail


def autorun_once(*, fill: bool = True, dry: bool = False) -> dict[str, Any]:
    """One intelligent autorun tick: fill → plan → drain or governor."""
    from mag.autorun_common import autorun_pause_reason

    result: dict[str, Any] = {
        "schema": "autorun_once.v1",
        "ts": _now(),
        "steps": [],
    }

    pause = autorun_pause_reason()
    if pause and not dry:
        result["action"] = "paused"
        result["detail"] = pause
        result["steps"].append({"paused": pause})
        _log_trail(result)
        return result

    if fill and not dry:
        filled = fill_queue()
        result["fill"] = filled
        result["steps"].append({"fill": filled.get("total_queued", 0)})

    plan = plan_pending()
    result["plan"] = plan
    result["steps"].append(
        {
            "plan": len(plan.get("orchestrator_queued") or []),
            "todo_mag": len(plan.get("todo_mag") or []),
        }
    )

    if dry:
        result["action"] = "dry"
        _log_trail(result)
        return result

    from mag.orchestrator import _any_running_task, drain_once, list_queue

    queued_n = sum(1 for q in list_queue() if q.get("status") == "queued")
    drain_res: dict[str, Any] | None = None
    if queued_n > 0 and not _any_running_task():
        drain_res = drain_once()
        result["drain"] = drain_res
        result["action"] = "drain"
        result["steps"].append({"drain": drain_res.get("action")})

    # Governor picks todo/agent_state when idle (or orchestrator drain failed).
    if not _any_running_task():
        from mag.governor import queue_candidates, run_cycle

        if queue_candidates() or not drain_res or drain_res.get("action") in (
            "empty",
            "spawn_failed",
        ):
            cyc = run_cycle(dry=False)
            result["governor"] = cyc
            if result.get("action") != "drain":
                result["action"] = "governor"
            result["steps"].append({"governor": cyc.get("action")})
    elif queued_n > 0:
        result["action"] = "busy"
        result["detail"] = "orchestrator task running"

    _log_trail(result)
    return result


def autorun_loop(interval_s: float = 5.0, *, once: bool = False) -> None:
    """Drainer main loop — intelligent fill/plan/execute."""
    fill_every = int(os.environ.get("MAG_AUTORUN_FILL_EVERY", "12") or "12")
    autopilot_every = int(os.environ.get("MAG_AUTOPILOT_EVERY", "0") or "0")
    tick = 0

    def _dim(s: str) -> str:
        if sys.stdout.isatty():
            return "\033[2m" + s + "\033[0m"
        return s

    while True:
        try:
            do_fill = tick == 0 or (fill_every > 0 and tick % fill_every == 0)
            res = autorun_once(fill=do_fill)
            action = res.get("action")
            if action == "drain":
                d = res.get("drain") or {}
                if d.get("action") in ("started", "spawn_failed"):
                    print(
                        _dim(f"  [autorun] drain {d.get('action')}: {d.get('goal', d.get('detail', ''))[:80]}"),
                        flush=True,
                    )
            elif action == "governor":
                g = res.get("governor") or {}
                if g.get("action") not in (None, "no_unblocked_work"):
                    print(
                        _dim(f"  [autorun] governor {g.get('action')} ok={g.get('ok')}: {str(g.get('detail', ''))[:80]}"),
                        flush=True,
                    )
            elif action == "busy":
                pass
        except Exception as e:
            print(_dim(f"  [autorun] error: {e}"), flush=True)

        tick += 1
        if autopilot_every > 0 and tick % autopilot_every == 0:
            try:
                from mag.autopilot import autopilot_once

                ap = autopilot_once(queue_improve=False, governor=False, drain=False)
                print(
                    _dim(f"  [autopilot] seed mirror: {str(ap.get('seed_mirror', {}).get('hint', '?'))[:60]}"),
                    flush=True,
                )
            except Exception as e:
                print(_dim(f"  [autopilot] error: {e}"), flush=True)

        if once:
            return
        time.sleep(interval_s)


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="governor_autorun", description="intelligent autorun cycle")
    ap.add_argument("--once", action="store_true", help="single tick then exit")
    ap.add_argument("--dry", action="store_true", help="plan only, no execute")
    ap.add_argument("--no-fill", action="store_true", help="skip queue fill")
    ap.add_argument("--fill-only", action="store_true", help="fill + plan only")
    ap.add_argument("--interval", type=float, default=5.0, help="loop interval seconds")
    args = ap.parse_args(argv)

    if args.fill_only:
        fill_queue()
        plan = plan_pending()
        print(json.dumps(plan, indent=2, default=str))
        return 0

    if args.once or args.dry:
        res = autorun_once(fill=not args.no_fill, dry=args.dry)
        print(json.dumps(res, indent=2, default=str))
        return 0

    autorun_loop(interval_s=args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
