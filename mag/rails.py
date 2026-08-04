"""Deterministic hard rails (Maelstrom V2 pattern) — machine-parseable constitution.

configs/constitutional_rails.json is the code-as-law contract checked at
preflight (Layer 1). Rails are regex/pattern rules with NO LLM involved:
block -> the tool call never reaches the OS.

Path rails mirror the legacy banned list in agent_cli._safe_tool_args
(defense in depth; rails file is the single editable source for new rules).
Content rails are the genuine delta: they catch live-looking secret values
being written into ordinary artifacts (path check alone misses those).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAILS_PATH = ROOT / "configs" / "constitutional_rails.json"

_EMPTY: dict = {"write_file_content": [], "write_file_path": []}


@lru_cache(maxsize=1)
def load_rails() -> dict:
    """Load the rails contract; on any failure degrade to empty (never crash preflight)."""
    try:
        if not RAILS_PATH.exists():
            return _EMPTY
        data = json.loads(RAILS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _EMPTY
        return data
    except Exception:
        return _EMPTY


def check_path(path: str) -> tuple[bool, str]:
    """Block writes whose path matches a path rail (residual DNA / knots / env)."""
    p = str(path or "").replace("\\", "/").lower()
    for rule in load_rails().get("write_file_path", []):
        for pat in rule.get("patterns", []):
            if pat.lower().replace("\\", "/") in p:
                return False, "rail[%s] blocked path: %s (%s)" % (
                    rule.get("id", "?"), pat, rule.get("desc", ""))
    return True, ""


def check_content(path: str, content: str) -> tuple[bool, str]:
    """Block writes whose content matches a content rail (live secret values)."""
    if not content:
        return True, ""
    for rule in load_rails().get("write_file_content", []):
        rx = rule.get("regex")
        if not rx:
            continue
        try:
            if re.search(rx, content):
                return False, "rail[%s] blocked content: %s" % (
                    rule.get("id", "?"), rule.get("desc", ""))
        except re.error:
            continue
    return True, ""


def check_write_file(path: str, content: str) -> tuple[bool, str]:
    """Combined preflight check for write_file (path then content)."""
    ok, msg = check_path(path)
    if not ok:
        return False, msg
    return check_content(path, content)
