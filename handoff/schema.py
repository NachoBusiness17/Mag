"""handoff.v1 contract validation."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED = {
    "schema",
    "id",
    "owner",
    "assignee",
    "tier",
    "goal",
    "ask",
    "success_checks",
    "return_path",
    "created_at",
}


def new_handoff(
    *,
    handoff_id: str,
    goal: str,
    ask: str,
    tier: str = "T3",
    success_checks: list[str] | None = None,
    inputs: dict | None = None,
    done_so_far: list | None = None,
    rollback: str = "Ignore result; keep prior working.md",
    return_path: str = "",
) -> dict[str, Any]:
    return {
        "schema": "handoff.v1",
        "id": handoff_id,
        "owner": "clerk",
        "assignee": "grok",
        "tier": tier,
        "goal": goal,
        "inputs": inputs or {"paths": [], "facts": [], "constraints": []},
        "done_so_far": done_so_far or [],
        "ask": ask,
        "success_checks": success_checks or ["Deliverable present in return_path"],
        "rollback": rollback,
        "return_path": return_path,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None,
    }


def validate_handoff(data: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return False, ["not a dict"]
    for k in REQUIRED:
        if k not in data:
            errors.append(f"missing: {k}")
    if data.get("schema") != "handoff.v1":
        errors.append("schema must be handoff.v1")
    if data.get("tier") not in {"T0", "T1", "T2", "T3"}:
        errors.append("tier invalid")
    if not isinstance(data.get("success_checks"), list):
        errors.append("success_checks must be list")
    return (len(errors) == 0, errors)


def write_handoff(path: Path, data: dict[str, Any]) -> None:
    ok, errs = validate_handoff(data)
    if not ok:
        raise ValueError(f"invalid handoff: {errs}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    md = path.with_suffix(".md")
    md.write_text(
        f"""# Handoff: {data.get('goal', '')}

- **id:** `{data['id']}`
- **tier:** {data.get('tier')}
- **assignee:** {data.get('assignee')}

## Ask

{data.get('ask')}

## Success checks

{chr(10).join('- ' + str(c) for c in data.get('success_checks') or [])}

## Return path

`{data.get('return_path')}`

## Rollback

{data.get('rollback')}
""",
        encoding="utf-8",
    )
