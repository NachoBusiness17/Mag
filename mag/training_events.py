"""Unified training events — orchestration labels for republic export (v3-005).

Append-only edges on Mag disk. Not a second DNA store.
Train in republic; import weights via promote. T0/T1 never export.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT

EVENTS_PATH = ROOT / "memory" / "training" / "events.jsonl"
SCHEMA = "mag_training_event.v1"

VALID_PATTERNS = frozenset({
    "route_decision",
    "autorun_cycle",
    "task_lifecycle",
    "steer_outcome",
    "fkb_failure",
    "spider_signal",
    "factory_cycle",
    "promote_gate",
    "resonance_hit",
})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event_id() -> str:
    return "evt-" + uuid.uuid4().hex[:12]


def emit(
    pattern: str,
    *,
    join: dict[str, str] | None = None,
    input_data: dict[str, Any] | None = None,
    action: dict[str, Any] | None = None,
    outcome: dict[str, Any] | None = None,
    pattern_tags: list[str] | None = None,
    tier_max: str = "T2",
    exportable: bool = True,
) -> dict[str, Any]:
    """Append one training event. Safe to call from any loop — failures are silent."""
    if pattern not in VALID_PATTERNS:
        pattern = "route_decision"
    row = {
        "schema": SCHEMA,
        "event_id": _event_id(),
        "ts": _now(),
        "pattern": pattern,
        "join": join or {},
        "input": input_data or {},
        "action": action or {},
        "outcome": outcome or {},
        "pattern_tags": pattern_tags or [],
        "tier_max": tier_max,
        "exportable": exportable,
    }
    try:
        EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with EVENTS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass
    return row


def read_events(*, limit: int = 500, pattern: str | None = None) -> list[dict[str, Any]]:
    if not EVENTS_PATH.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in EVENTS_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if pattern and row.get("pattern") != pattern:
            continue
        rows.append(row)
    return rows[-limit:]


def _redact_t2(row: dict[str, Any]) -> dict[str, Any]:
    """Strip fields that should not leave operator disk on export."""
    out = dict(row)
    if not out.get("exportable", True):
        return {}
    goal = str((out.get("input") or {}).get("goal") or "")
    if len(goal) > 400:
        (out.setdefault("input", {}))["goal"] = goal[:400] + "…"
    return out


def export_jsonl(
    *,
    dest: Path | None = None,
    tier_max: str = "T2",
    pattern: str | None = None,
    limit: int = 5000,
) -> dict[str, Any]:
    rows = read_events(limit=limit, pattern=pattern)
    exported = [_redact_t2(r) for r in rows if r.get("exportable", True)]
    exported = [r for r in exported if r]
    out_path = dest or (ROOT / "memory" / "training" / "export" / f"orch_train_{_now()[:10]}.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in exported:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return {
        "ok": True,
        "schema": SCHEMA,
        "tier_max": tier_max,
        "n_read": len(rows),
        "n_exported": len(exported),
        "path": str(out_path),
    }


def stats() -> dict[str, Any]:
    rows = read_events(limit=10000)
    by_pattern: dict[str, int] = {}
    for r in rows:
        p = str(r.get("pattern") or "unknown")
        by_pattern[p] = by_pattern.get(p, 0) + 1
    return {
        "schema": SCHEMA,
        "path": str(EVENTS_PATH),
        "total": len(rows),
        "by_pattern": by_pattern,
        "exportable": sum(1 for r in rows if r.get("exportable", True)),
    }
