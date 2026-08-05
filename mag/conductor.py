"""L-conductor — orchestration policy overlay (v3-009 research).

Wraps route.v2 with phase detection and case-law hints. Does not replace
frontier execution — conductor picks the seat; specialists work.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT

CONDUCTOR_TRAIL = ROOT / "memory" / "runs" / "conductor_trail.jsonl"

_PHASE_MARKERS = {
    "plan": ("[priority]", "plan only", "build spec", "acceptance", "architecture"),
    "build": ("[build]", "implement", "cursor/", "pytest", "branch"),
    "audit": ("audit only", "ponytail", "routing_smoke", "verdict:", "diff review"),
    "defer": ("wait_human", "blocked", "pause", "operator active"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trail(goal: str, phase: str, route: dict[str, Any]) -> None:
    CONDUCTOR_TRAIL.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": _now(),
        "goal": goal[:200],
        "phase": phase,
        "seat": route.get("seat"),
        "provider": route.get("provider"),
        "depth": route.get("depth"),
    }
    with CONDUCTOR_TRAIL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    try:
        from mag.training_events import emit

        emit(
            "route_decision",
            join={},
            input_data={"goal": goal[:200], "phase": phase},
            action={
                "seat": route.get("seat"),
                "provider": route.get("provider"),
                "depth": route.get("depth"),
                "route_schema": route.get("schema", "route.v2"),
            },
            outcome={"label_source": "heuristic"},
            pattern_tags=[f"phase_{phase}"],
        )
    except Exception:
        pass


def detect_phase(goal: str) -> str:
    g = (goal or "").lower()
    scores = {phase: 0 for phase in _PHASE_MARKERS}
    for phase, markers in _PHASE_MARKERS.items():
        for m in markers:
            if m in g:
                scores[phase] += 1
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return "execute"
    return best


def _case_law_hints(goal: str, *, limit: int = 2) -> list[str]:
    path = ROOT / "memory" / "decisions_log.jsonl"
    if not path.is_file():
        return []
    tokens = {t for t in re.findall(r"[a-z0-9]{3,}", goal.lower())}
    hints: list[tuple[int, str]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        blob = f"{row.get('context', '')} {row.get('outcome', '')}".lower()
        overlap = len(tokens & {t for t in re.findall(r"[a-z0-9]{3,}", blob)})
        if overlap > 0:
            hints.append((overlap, str(row.get("outcome") or row.get("context") or "")[:120]))
    hints.sort(key=lambda x: x[0], reverse=True)
    return [h for _, h in hints[:limit]]


def conduct(
    goal: str,
    *,
    depth: str | None = None,
    force_seat: str | None = None,
    force_provider: str | None = None,
    dry: bool = False,
) -> dict[str, Any]:
    from mag.router import route

    phase = detect_phase(goal)
    base = route(
        goal,
        depth=depth,
        force_seat=force_seat,
        force_provider=force_provider,
    )
    hints = _case_law_hints(goal)

    # Phase overlays — research heuristics, not learned weights yet
    overlay: dict[str, Any] = {"phase": phase, "case_law_hints": hints}
    if phase == "plan" and not force_seat:
        overlay["conductor_note"] = "Scarce architect seat — spec only, no implementation"
        if base.get("seat") not in ("grok_tui", "human", "defer"):
            overlay["suggested_seat"] = "grok_tui"
    elif phase == "build":
        overlay["conductor_note"] = "Factory floor — frozen spec required; one branch"
        overlay["suggested_seat"] = "agent"
    elif phase == "audit":
        overlay["conductor_note"] = "Inspector — framework gates only; no feature creep"
        overlay["suggested_seat"] = "defer"
    elif phase == "defer":
        overlay["conductor_note"] = "Human gate or pause — do not autorun"

    out = {
        "schema": "conductor.v1",
        "ts": _now(),
        "goal": goal[:300],
        "phase": phase,
        "route": base,
        "overlay": overlay,
        "dry": dry,
    }
    if not dry:
        _trail(goal, phase, base)
    return out
