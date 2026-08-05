"""Skill seats — ponytail / caveman as agent modes.

Loads weave preambles, picks skill by goal, runs audit gates.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from config import ROOT

SKILL_WEAVES: dict[str, str] = {
    "ponytail": "memory/improve/weaves/W8-ponytail-ladder.md",
    "caveman": "memory/improve/weaves/W9-caveman-prose.md",
}

_CODE_MARKERS = (
    "implement", "fix", "refactor", "pytest", "main.py", "mag/", "cursor/",
    "branch", "diff", "audit only", "ponytail", "routing_smoke", "[build]",
)
_DOC_MARKERS = (
    "plan only", "spec", "handoff", "acceptance", "architecture", "[priority]",
    "docs/", "BUILD", "one line", "anti-goal", "caveman",
)


def load_skill(skill_id: str) -> str:
    rel = SKILL_WEAVES.get(skill_id)
    if not rel:
        return ""
    p = ROOT / rel
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def pick_skill_for_goal(goal: str) -> str:
    g = (goal or "").lower()
    doc_score = sum(1 for m in _DOC_MARKERS if m in g)
    code_score = sum(1 for m in _CODE_MARKERS if m in g)
    if "caveman" in g:
        return "caveman"
    if "ponytail" in g:
        return "ponytail"
    if doc_score > code_score:
        return "caveman"
    if code_score > doc_score:
        return "ponytail"
    return "ponytail"


def build_preamble(skill_id: str, *, goal: str = "") -> str:
    body = load_skill(skill_id)
    if not body:
        return ""
    return f"[MAG SKILL SEAT: {skill_id}]\n{body}\n\nGOAL: {goal[:400]}\n"


def run_gate(skill_id: str, *, path: str = "") -> dict[str, Any]:
    if skill_id == "ponytail":
        from mag.ponytail_audit import run_audit

        res = run_audit(hints=True)
        res["skill"] = "ponytail"
        res["pass"] = bool(res.get("lean"))
        return res
    if skill_id == "caveman":
        from mag.caveman_audit import run_audit

        paths = [path] if path else None
        res = run_audit(paths=paths)
        res["skill"] = "caveman"
        res["pass"] = bool(res.get("dense"))
        return res
    return {"ok": False, "error": f"unknown skill: {skill_id}"}


def skill_status() -> dict[str, Any]:
    return {
        "schema": "mag_skill_seat.v1",
        "skills": {
            sid: {"path": rel, "on_disk": (ROOT / rel).is_file()}
            for sid, rel in SKILL_WEAVES.items()
        },
        "gates": {
            "ponytail": "python main.py ponytail-audit",
            "caveman": "python main.py caveman-audit",
        },
    }
