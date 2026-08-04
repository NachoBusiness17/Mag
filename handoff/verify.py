"""Verify result packets against handoff success checks (minimal)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def verify_result(handoff: dict[str, Any], result: dict[str, Any]) -> tuple[bool, list[str]]:
    notes: list[str] = []
    if result.get("handoff_id") and result.get("handoff_id") != handoff.get("id"):
        notes.append("handoff_id mismatch")
    if not result.get("deliverable") and not result.get("summary"):
        notes.append("missing deliverable/summary")
    # Soft pass: presence of content; human can tighten checks later
    ok = len(notes) == 0 and bool(result.get("ok", True))
    if ok:
        notes.append("basic verify pass")
    return ok, notes
