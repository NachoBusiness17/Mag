"""Append-only router log + CURRENT.md sync."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import CURRENT_MD, LOGS_DIR, ROUTER_LOG


def log_event(event: dict[str, Any]) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    with ROUTER_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, default=str) + "\n")


def sync_current(state: dict[str, Any]) -> None:
    CURRENT_MD.parent.mkdir(parents=True, exist_ok=True)
    plan = state.get("plan") or []
    plan_txt = "\n".join(f"- {s}" for s in plan) if plan else "- (none)"
    trace = state.get("tool_trace") or []
    last_tools = "\n".join(
        f"- {t.get('tool')}: exit={t.get('exit_code')} ok={t.get('ok')}" for t in trace[-5:]
    ) or "- (none)"
    body = f"""# CURRENT

- **status:** {state.get('status')}
- **tier:** {state.get('tier')}
- **route:** {state.get('route')}
- **step_i:** {state.get('step_i')}
- **handoff_id:** {state.get('handoff_id')}
- **updated:** {datetime.now(timezone.utc).isoformat()}

## Goal

{state.get('goal')}

## Plan

{plan_txt}

## Last result

{(state.get('last_result') or '')[:2000]}

## Critique

{(state.get('critique') or '')[:1500]}

## Recent tools

{last_tools}
"""
    CURRENT_MD.write_text(body, encoding="utf-8")
