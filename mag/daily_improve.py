"""Daily improve scheduling — orchestrator-owned, 08:00 America/New_York default.

Scout/eval/field_brief stay L0 local (improve --once). Top tickets enqueue to
DeepSeek via the orchestrator queue — the drainer picks them up after scout.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from config import ROOT

SCHEDULE_STATE = ROOT / "state" / "daily_improve.json"
MAG_CMD_PREFIX = "[mag-cmd] "
DAILY_TAG = "MagImproveDaily"
DAILY_GOAL = "[mag-cmd] daily-improve"


def _now_iso() -> str:
    from datetime import timezone

    return datetime.now(timezone.utc).isoformat()


def _load_schedule_state() -> dict[str, Any]:
    if not SCHEDULE_STATE.is_file():
        return {}
    try:
        data = json.loads(SCHEDULE_STATE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_schedule_state(state: dict[str, Any]) -> None:
    SCHEDULE_STATE.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_STATE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def improve_daily_timezone() -> ZoneInfo:
    from mag.preferences import load_prefs

    tz_name = (
        os.environ.get("MAG_IMPROVE_TZ", "").strip()
        or load_prefs().get("improve_daily_tz")
        or "America/New_York"
    )
    try:
        return ZoneInfo(str(tz_name))
    except Exception:
        return ZoneInfo("America/New_York")


def _day_str_local(tz: ZoneInfo | None = None) -> str:
    tz = tz or improve_daily_timezone()
    return datetime.now(tz).strftime("%Y-%m-%d")


def is_daily_improve_due() -> bool:
    """True when local hour >= configured hour and today's scout has not run."""
    from mag.improve import scout_due_today
    from mag.preferences import improve_daily_enabled, improve_daily_hour

    if not improve_daily_enabled():
        return False
    if not scout_due_today():
        return False
    tz = improve_daily_timezone()
    now = datetime.now(tz)
    return now.hour >= improve_daily_hour()


def _queue_has_daily_job() -> bool:
    from mag.orchestrator import list_queue

    for q in list_queue(limit=50):
        if q.get("tag") != DAILY_TAG:
            continue
        if q.get("status") in ("queued", "running"):
            return True
    return False


def run_daily_improve(*, max_queue: int = 2, queue_deepseek: bool = True) -> dict[str, Any]:
    """L0 scout + field brief, then enqueue top improve tickets for DeepSeek."""
    from mag.improve import improve_once

    out: dict[str, Any] = {"ok": True, "schema": "daily_improve.v1", "ts": _now_iso()}
    imp = improve_once()
    out["improve"] = imp
    if not imp.get("ok"):
        out["ok"] = False

    queued: list[dict[str, Any]] = []
    if queue_deepseek and imp.get("ok"):
        try:
            from mag.autopilot import _top_improve_candidates
            from mag.orchestrator import enqueue

            for cand in _top_improve_candidates(max_queue):
                claim = str(cand.get("claim") or cand.get("id") or "")[:300]
                if not claim:
                    continue
                goal = f"[improve] {claim}"
                cid = str(cand.get("id") or "")[:12]
                rec = enqueue(
                    goal,
                    provider="deepseek",
                    tag=f"improve-{cid}",
                )
                queued.append(rec)
        except Exception as e:
            out["queue_error"] = str(e)
    out["queued"] = queued
    out["queued_n"] = len(queued)

    state = _load_schedule_state()
    state["last_run"] = _now_iso()
    state["last_run_day"] = _day_str_local()
    state["scheduled_day"] = _day_str_local()
    state["last_ok"] = out.get("ok")
    state["queued_n"] = len(queued)
    _save_schedule_state(state)
    return out


def maybe_schedule_daily_improve() -> dict[str, Any] | None:
    """Enqueue daily-improve on the orchestrator queue when the slot is due.

    Called from the drainer loop. Requires drainer ON — scout runs as an
    isolated subprocess; DeepSeek tickets enqueue at the end of daily-improve.
    """
    if not is_daily_improve_due():
        return None

    day = _day_str_local()
    state = _load_schedule_state()
    if state.get("scheduled_day") == day:
        return None
    if _queue_has_daily_job():
        state["scheduled_day"] = day
        _save_schedule_state(state)
        return None

    from mag.orchestrator import enqueue

    rec = enqueue(
        DAILY_GOAL,
        provider="ollama",
        tag=DAILY_TAG,
        timeout=900,
    )
    state["scheduled_day"] = day
    state["last_enqueued_at"] = _now_iso()
    state["queue_id"] = rec.get("queue_id")
    _save_schedule_state(state)
    return rec


def schedule_status() -> dict[str, Any]:
    """Payload for dashboard / router."""
    from mag.improve import improve_light_status
    from mag.preferences import drainer_enabled, improve_daily_enabled, improve_daily_hour, load_prefs

    env = os.environ.get("MAG_IMPROVE_DAILY", "").strip().lower()
    pref_val = load_prefs().get("improve_daily")
    locked = env in ("1", "true", "yes", "0", "false", "no")
    tz = improve_daily_timezone()
    now = datetime.now(tz)
    st = _load_schedule_state()
    loop = improve_light_status()
    hour = improve_daily_hour()
    enabled = improve_daily_enabled()
    drainer = drainer_enabled()

    if locked:
        hint = "MAG_IMPROVE_DAILY env overrides dashboard toggle"
    elif not enabled:
        hint = "Daily improve off"
    elif not drainer:
        hint = f"Due ~{hour:02d}:00 {tz.key} — turn on drainer for orchestrator run"
    elif is_daily_improve_due():
        hint = "Due now — drainer enqueues MagImproveDaily → scout local, tickets DeepSeek"
    else:
        hint = f"Next slot ~{hour:02d}:00 {tz.key} · drainer picks up orchestrator queue"

    return {
        "enabled": enabled,
        "pref": bool(pref_val) if pref_val is not None else True,
        "hour": hour,
        "timezone": str(tz),
        "env": env or None,
        "env_locked": locked,
        "drainer": drainer,
        "hint": hint,
        **loop,
        "local_now": now.isoformat(),
        "local_hour": now.hour,
        "due_now": is_daily_improve_due(),
        "scheduled_day": st.get("scheduled_day"),
        "last_enqueued_at": st.get("last_enqueued_at"),
        "last_run": st.get("last_run"),
        "last_run_day": st.get("last_run_day"),
        "queue_id": st.get("queue_id"),
        "orchestrator_tag": DAILY_TAG,
        "orchestrator_goal": DAILY_GOAL,
        "slot": f"{hour:02d}:00 {tz.key}",
        "path": "orchestrator queue → drainer (scout local, tickets DeepSeek)",
    }
