"""Per-provider usage + remaining-until-reset tracking.

Platforms rarely expose free-tier remainder via API. We:
  1. Record every remote/local call (calls + estimated tokens)
  2. Apply user-set period limits from providers.yaml
  3. Expose remaining for the router

Reset periods: daily (UTC midnight), monthly (reset_day), none (unlimited).
"""
from __future__ import annotations

import json
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import ROOT

STATE_PATH = ROOT / "logs" / "quota_state.json"
USAGE_DETAIL = ROOT / "logs" / "provider_usage.jsonl"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _period_bounds(period: str, reset_day: int = 1, now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or _now()
    period = (period or "monthly").lower()
    if period in ("none", "unlimited", ""):
        # far future
        return now - timedelta(days=3650), now + timedelta(days=3650)
    if period == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return start, end
    # monthly
    rd = max(1, min(28, int(reset_day or 1)))
    if now.day >= rd:
        start = now.replace(day=rd, hour=0, minute=0, second=0, microsecond=0)
        # next month
        if now.month == 12:
            end = now.replace(year=now.year + 1, month=1, day=rd, hour=0, minute=0, second=0, microsecond=0)
        else:
            end = now.replace(month=now.month + 1, day=rd, hour=0, minute=0, second=0, microsecond=0)
    else:
        # period started last month
        if now.month == 1:
            start = now.replace(year=now.year - 1, month=12, day=rd, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now.replace(month=now.month - 1, day=rd, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(day=rd, hour=0, minute=0, second=0, microsecond=0)
    return start, end


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {"providers": {}, "updated": None}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"providers": {}, "updated": None}


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["updated"] = _now().isoformat()
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def record_usage(
    provider_id: str,
    *,
    model: str = "",
    calls: int = 1,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    ok: bool = True,
    meta: dict | None = None,
) -> None:
    total_tok = int(prompt_tokens or 0) + int(completion_tokens or 0)
    # estimate if missing
    if total_tok <= 0 and meta and meta.get("chars"):
        total_tok = max(1, int(meta["chars"]) // 4)

    state = _load_state()
    prov = state.setdefault("providers", {}).setdefault(
        provider_id,
        {"calls": 0, "tokens": 0, "period_start": None, "period_end": None},
    )
    # roll period if needed — bounds stored as iso
    from models.providers import get_provider

    pcfg = get_provider(provider_id) or {}
    q = pcfg.get("quota") or {}
    period = str(q.get("period") or "monthly")
    start, end = _period_bounds(period, int(q.get("reset_day") or 1))
    ps = prov.get("period_start")
    # "none"/unlimited: never roll counters on sliding window
    if period not in ("none", "unlimited", ""):
        roll = False
        if not ps:
            roll = True
        else:
            try:
                ps_dt = datetime.fromisoformat(str(ps).replace("Z", "+00:00"))
                if ps_dt < start:
                    roll = True
            except ValueError:
                roll = True
        if roll:
            prov["calls"] = 0
            prov["tokens"] = 0
            prov["period_start"] = start.isoformat()
            prov["period_end"] = end.isoformat()
    else:
        prov.setdefault("period_start", start.isoformat())
        prov.setdefault("period_end", end.isoformat())
    prov["calls"] = int(prov.get("calls") or 0) + calls
    prov["tokens"] = int(prov.get("tokens") or 0) + total_tok
    prov["last_model"] = model
    prov["last_ok"] = ok
    prov["last_ts"] = _now().isoformat()
    _save_state(state)

    USAGE_DETAIL.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": _now().isoformat(),
        "provider": provider_id,
        "model": model,
        "calls": calls,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tokens": total_tok,
        "ok": ok,
        "meta": meta or {},
    }
    with USAGE_DETAIL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")

    try:
        from mag.lanes import log_usage

        log_usage(
            lane="L1" if provider_id != "ollama" else "L0",
            action="provider_chat",
            detail=f"{provider_id}:{model}",
            ok=ok,
            meta=row,
        )
    except Exception:
        pass


def provider_budget(provider_id: str) -> dict[str, Any]:
    from models.providers import get_provider

    pcfg = get_provider(provider_id) or {}
    q = pcfg.get("quota") or {}
    period = str(q.get("period") or "monthly")
    start, end = _period_bounds(period, int(q.get("reset_day") or 1))
    state = _load_state()
    prov = (state.get("providers") or {}).get(provider_id) or {}
    # roll display counters only for finite periods
    if period not in ("none", "unlimited", ""):
        ps = prov.get("period_start")
        if ps:
            try:
                ps_dt = datetime.fromisoformat(str(ps).replace("Z", "+00:00"))
                if ps_dt < start:
                    prov = {"calls": 0, "tokens": 0}
            except ValueError:
                pass
    used_c = int(prov.get("calls") or 0)
    used_t = int(prov.get("tokens") or 0)
    max_c = q.get("max_calls")
    max_t = q.get("max_tokens")
    unlimited = period in ("none", "unlimited") or (max_c is None and max_t is None)

    rem_c = None if max_c is None else max(0, int(max_c) - used_c)
    rem_t = None if max_t is None else max(0, int(max_t) - used_t)
    ok = True
    if not unlimited:
        if rem_c is not None and rem_c <= 0:
            ok = False
        if rem_t is not None and rem_t <= 0:
            ok = False

    seconds_left = max(0, int((end - _now()).total_seconds()))
    return {
        "provider": provider_id,
        "name": pcfg.get("name") or provider_id,
        "period": period,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "seconds_until_reset": seconds_left,
        "reset_in_hours": round(seconds_left / 3600, 1),
        "used_calls": used_c,
        "used_tokens": used_t,
        "max_calls": max_c,
        "max_tokens": max_t,
        "remaining_calls": rem_c,
        "remaining_tokens": rem_t,
        "budget_ok": ok or unlimited,
        "unlimited": unlimited,
        "configured": _provider_configured(provider_id, pcfg),
        "note": q.get("note") or "",
    }


def _provider_configured(pid: str, pcfg: dict) -> bool:
    if pcfg.get("free_local"):
        return True
    env = pcfg.get("api_key_env")
    if not env:
        return bool(pcfg.get("api_key_default"))
    import os

    keys = [env]
    if env == "OPENROUTER_API_KEY":
        keys.append("OR_API_KEY")
    if env == "GEMINI_API_KEY":
        keys.append("GOOGLE_API_KEY")
    return any(os.environ.get(k) for k in keys)


def all_budgets() -> dict[str, Any]:
    from models.providers import list_provider_ids

    rows = [provider_budget(pid) for pid in list_provider_ids()]
    return {
        "ok": True,
        "ts": _now().isoformat(),
        "providers": rows,
        "routing_hint": "Prefer providers with budget_ok and configured; ollama first for private.",
    }


def pick_provider(
    job: str = "default",
    *,
    tier: str = "T2",
    prefer: list[str] | None = None,
) -> dict[str, Any]:
    """Pick first provider with key + budget, respecting tier and job list."""
    from models.providers import get_provider, load_providers, list_provider_ids

    cfg = load_providers()
    never = set((cfg.get("defaults") or {}).get("never_remote_tiers") or ["T0", "T1"])
    order = prefer or (cfg.get("routing") or {}).get(job) or (cfg.get("defaults") or {}).get("prefer_order") or list_provider_ids()

    candidates = []
    for pid in order:
        p = get_provider(pid)
        if not p:
            continue
        b = provider_budget(pid)
        tier_max = p.get("tier_max") or "T2"
        # private tiers: only free_local
        if tier in never and not p.get("free_local"):
            candidates.append({**b, "skip": "tier_block", "eligible": False})
            continue
        if not b.get("configured"):
            candidates.append({**b, "skip": "no_api_key", "eligible": False})
            continue
        if not b.get("budget_ok"):
            candidates.append({**b, "skip": "quota_exhausted", "eligible": False})
            continue
        # ok
        return {
            "ok": True,
            "provider": pid,
            "model": p.get("default_model"),
            "budget": b,
            "candidates": candidates,
        }
    return {
        "ok": False,
        "error": "no provider with key+budget",
        "candidates": candidates,
        "hint": "Set an API key env var or raise quota in configs/providers.yaml; or use ollama",
    }
