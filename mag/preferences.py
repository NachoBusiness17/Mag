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


def autonomy_status() -> dict:
    prefs = load_prefs()
    return {
        "inject_behavioral_pack": inject_behavioral_pack(),
        "drainer": drainer_enabled(),
        "compass_autonomous_continue": True,
        "note": (
            "Ambiguous input (continue/go) is wrapped by compass — agent decides from blueprint + case law, "
            "not raw prompt. Toggle inject_behavioral_pack to teach recurring errors in every LOAD."
        ),
    }
