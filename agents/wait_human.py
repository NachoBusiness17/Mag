"""WAIT_HUMAN — structured ask on disk."""
from __future__ import annotations

from datetime import datetime, timezone

from audit import log_event, sync_current
from config import QUEUE_DIR
from state import AgentState


def wait_human_node(state: AgentState) -> dict:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    path = QUEUE_DIR / "wait_human.md"
    body = f"""# Waiting on human

- **when:** {datetime.now(timezone.utc).isoformat()}
- **tier:** {state.get('tier')}
- **goal:** {state.get('goal')}

## Why

{(state.get('critique') or state.get('last_result') or 'Router requested human input.')[:2000]}

## What we need from you

Reply in working.md or re-run with a clearer goal. If T0 secrets were involved, handle offline — do not paste secrets into free remote models.
"""
    path.write_text(body, encoding="utf-8")
    out = {"status": "waiting", "last_result": f"Waiting: see {path}"}
    log_event({"node": "wait_human", "path": str(path)})
    sync_current({**state, **out})
    return out
