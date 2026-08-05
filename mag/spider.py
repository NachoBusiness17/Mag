"""Spider — meta-supervisor on the agent web (v3-007 research, Phase 0 rules).

Read-only watcher across orchestrator children, autorun trail, FKB recurrence.
Emits steer signals via pigeonhole — never spawns a second orchestrator.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT

SPIDER_TRAIL = ROOT / "memory" / "runs" / "spider_trail.jsonl"
STALL_THRESHOLD_S = 180
FKB_REPEAT_THRESHOLD = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trail(event: str, **fields: Any) -> None:
    SPIDER_TRAIL.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": _now(), "event": event, **fields}
    with SPIDER_TRAIL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _read_jsonl_tail(path: Path, n: int = 20) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    for line in lines[-n:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _check_orchestrator_tasks() -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    try:
        from mag import orchestrator as orc
        from mag import pigeonhole as ph

        for task in orc.list_tasks_live() or []:
            tid = task.get("id") or task.get("task_id")
            if not tid:
                continue
            status = task.get("status")
            if status in orc.TERMINAL:
                continue
            age = ph.staleness_s(str(tid))
            if age is not None and age >= STALL_THRESHOLD_S:
                signals.append({
                    "kind": "stall",
                    "severity": "warn",
                    "task_id": tid,
                    "age_s": age,
                    "action": "steer",
                    "message": f"Task {tid} stalled {age}s — spider recommends steer",
                })
    except Exception as exc:
        signals.append({
            "kind": "spider_error",
            "severity": "info",
            "message": f"orchestrator probe failed: {exc}",
        })
    return signals


def _check_autorun_trail() -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    trail = ROOT / "memory" / "runs" / "governor_autorun_trail.jsonl"
    rows = _read_jsonl_tail(trail, 30)
    fails = [r for r in rows if r.get("event") in ("fail", "error", "blocked")]
    if len(fails) >= 3:
        signals.append({
            "kind": "autorun_fail_burst",
            "severity": "warn",
            "count": len(fails),
            "action": "pause_suggest",
            "message": "Autorun trail shows repeated failures — consider MAG_OPERATOR_ACTIVE",
        })
    return signals


def _check_fkb_repeat() -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    try:
        from mag.failure_kb import recurring_patterns

        for pat in recurring_patterns(limit=5) or []:
            count = int(pat.get("count") or 0)
            if count >= FKB_REPEAT_THRESHOLD:
                signals.append({
                    "kind": "fkb_repeat",
                    "severity": "warn",
                    "signature": pat.get("signature") or pat.get("key"),
                    "count": count,
                    "action": "surface_remedy",
                    "message": f"FKB pattern repeated {count}x — remedy may exist",
                })
    except Exception:
        pass
    return signals


def _check_operator_active() -> list[dict[str, Any]]:
    import os

    if os.environ.get("MAG_OPERATOR_ACTIVE", "").strip().lower() in ("1", "true", "yes"):
        return [{
            "kind": "operator_active",
            "severity": "info",
            "action": "defer_autorun",
            "message": "MAG_OPERATOR_ACTIVE — spider defers proactive steer on autorun",
        }]
    return []


def _check_cloud_seats() -> list[dict[str, Any]]:
    """Stale cloud/desktop external seats — orphan detection."""
    signals: list[dict[str, Any]] = []
    try:
        from mag.seat_registry import list_registered

        for seat in list_registered(live_only=True):
            age = seat.get("heartbeat_age_s")
            src = str(seat.get("source") or seat.get("parent") or "")
            if age is not None and age >= STALL_THRESHOLD_S:
                signals.append({
                    "kind": "cloud_seat_stale",
                    "severity": "warn",
                    "task_id": seat.get("task_id"),
                    "age_s": age,
                    "source": src,
                    "action": "steer",
                    "message": f"External seat {seat.get('task_id')} stale {age}s — heartbeat or unregister",
                })
    except Exception:
        pass
    return signals


def tick(*, dry: bool = False, inject: bool = False) -> dict[str, Any]:
    signals = []
    signals.extend(_check_operator_active())
    signals.extend(_check_orchestrator_tasks())
    signals.extend(_check_cloud_seats())
    signals.extend(_check_autorun_trail())
    signals.extend(_check_fkb_repeat())

    injected = []
    reaped = None
    if inject and not dry:
        from mag import pigeonhole as ph

        for sig in signals:
            if sig.get("action") != "steer":
                continue
            tid = sig.get("task_id")
            if not tid:
                continue
            msg = f"[spider] {sig.get('message', 'course correct')}"
            ph.post_steer(str(tid), msg[:400])
            injected.append(tid)

    if not dry:
        try:
            from mag.switchboard import find_orphans, reap

            orphans = find_orphans(dry=True)
            if orphans.get("n", 0) > 0:
                reaped = reap()
                signals.append({
                    "kind": "orphan_reap",
                    "severity": "info",
                    "count": orphans.get("n"),
                    "action": "reap",
                    "message": f"Switchboard reaped {reaped.get('reaped', 0)} stale; {orphans.get('n')} orphan(s) noted",
                })
        except Exception:
            pass

    _trail("tick", dry=dry, n_signals=len(signals), injected=injected)
    try:
        from mag.training_events import emit

        for sig in signals:
            emit(
                "spider_signal",
                input_data={"message": sig.get("message", "")[:200]},
                action={"kind": sig.get("kind"), "severity": sig.get("severity")},
                outcome={"injected": sig.get("task_id") in injected if injected else False},
                pattern_tags=[str(sig.get("kind") or "signal")],
            )
    except Exception:
        pass
    return {
        "schema": "spider_tick.v1",
        "ts": _now(),
        "ok": True,
        "dry": dry,
        "signals": signals,
        "injected": injected,
        "reaped": reaped,
        "n_signals": len(signals),
    }
