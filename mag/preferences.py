"""Operator preferences persisted for the supervisor (drainer toggle, etc.)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from config import ROOT

PREF_PATH = ROOT / "state" / "mag_preferences.json"


def load_prefs() -> dict:
    if not PREF_PATH.is_file():
        return {}
    try:
        data = json.loads(PREF_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_prefs(prefs: dict) -> None:
    PREF_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREF_PATH.write_text(json.dumps(prefs, indent=2, default=str), encoding="utf-8")


def drainer_enabled() -> bool:
    env = os.environ.get("MAG_DRAINER", "").strip().lower()
    if env in ("1", "true", "yes"):
        return True
    if env in ("0", "false", "no"):
        return False
    return bool(load_prefs().get("drainer"))


def set_drainer(enabled: bool) -> dict:
    prefs = load_prefs()
    prefs["drainer"] = bool(enabled)
    prefs["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_prefs(prefs)
    return prefs


def drainer_status() -> dict:
    env = os.environ.get("MAG_DRAINER", "").strip().lower()
    pref = bool(load_prefs().get("drainer"))
    locked = env in ("1", "true", "yes", "0", "false", "no")
    return {
        "enabled": drainer_enabled(),
        "pref": pref,
        "env": env or None,
        "env_locked": locked,
        "hint": (
            "MAG_DRAINER env overrides dashboard toggle"
            if locked
            else "Supervisor picks this up within ~5s"
        ),
    }


def inject_behavioral_pack() -> bool:
    """Include behavioral themes + compass framework in context-pack (default on)."""
    if os.environ.get("MAG_NO_BEHAVIORAL_PACK", "").strip().lower() in ("1", "true", "yes"):
        return False
    return load_prefs().get("inject_behavioral_pack", True) is not False


def set_inject_behavioral_pack(enabled: bool) -> dict:
    prefs = load_prefs()
    prefs["inject_behavioral_pack"] = bool(enabled)
    prefs["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_prefs(prefs)
    return prefs


def improve_daily_enabled() -> bool:
    """Daily improve via orchestrator drainer (default ON; opt-out with env/pref)."""
    env = os.environ.get("MAG_IMPROVE_DAILY", "").strip().lower()
    if env in ("0", "false", "no"):
        return False
    if env in ("1", "true", "yes"):
        return True
    prefs = load_prefs()
    if "improve_daily" in prefs:
        return bool(prefs["improve_daily"])
    return True


def improve_daily_hour() -> int:
    pref = load_prefs().get("improve_daily_hour")
    try:
        h = int(pref if pref is not None else 8)
    except (TypeError, ValueError):
        h = 8
    return max(0, min(h, 23))


def improve_daily_tz_name() -> str:
    env = os.environ.get("MAG_IMPROVE_TZ", "").strip()
    if env:
        return env
    return str(load_prefs().get("improve_daily_tz") or "America/New_York")


def set_improve_daily(
    enabled: bool,
    *,
    hour: int | None = None,
    tz: str | None = None,
) -> dict:
    prefs = load_prefs()
    prefs["improve_daily"] = bool(enabled)
    if hour is not None:
        prefs["improve_daily_hour"] = max(0, min(int(hour), 23))
    if tz is not None and tz.strip():
        prefs["improve_daily_tz"] = tz.strip()
    prefs["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_prefs(prefs)
    return prefs


def improve_daily_status() -> dict:
    """Dashboard payload: prefs + improve loop residue."""
    try:
        from mag.daily_improve import schedule_status

        return schedule_status()
    except Exception as e:
        env = os.environ.get("MAG_IMPROVE_DAILY", "").strip().lower()
        pref = bool(load_prefs().get("improve_daily"))
        locked = env in ("1", "true", "yes", "0", "false", "no")
        return {
            "enabled": improve_daily_enabled(),
            "pref": pref,
            "hour": improve_daily_hour(),
            "timezone": improve_daily_tz_name(),
            "env": env or None,
            "env_locked": locked,
            "error": str(e)[:200],
            "hint": "Daily improve status unavailable",
        }


def autonomy_status() -> dict:
    prefs = load_prefs()
    return {
        "inject_behavioral_pack": inject_behavioral_pack(),
        "drainer": drainer_enabled(),
        "improve_daily": improve_daily_enabled(),
        "compass_autonomous_continue": True,
        "note": (
            "Ambiguous input (continue/go) is wrapped by compass — agent decides from blueprint + case law, "
            "not raw prompt. Toggle inject_behavioral_pack to teach recurring errors in every LOAD."
        ),
    }
