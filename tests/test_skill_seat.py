"""Ponytail / caveman skill seats."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_pick_skill_code():
    from mag.skill_seat import pick_skill_for_goal

    assert pick_skill_for_goal("implement pytest fix mag/router.py") == "ponytail"
    assert pick_skill_for_goal("[priority] plan only BUILD spec acceptance") == "caveman"


def test_weaves_on_disk():
    from mag.skill_seat import load_skill

    assert "YAGNI" in load_skill("ponytail")
    assert "terse" in load_skill("caveman").lower()


def test_ponytail_gate():
    from mag.skill_seat import run_gate

    res = run_gate("ponytail")
    assert res.get("skill") == "ponytail"
    assert "lean" in res or "pass" in res


def test_caveman_audit_runs():
    from mag.caveman_audit import run_audit

    res = run_audit(paths=["docs/ref/PONYTAIL_CAVEMAN_AUDIT.md"])
    assert res.get("schema") == "caveman_audit.v1"


def test_conductor_skill_overlay():
    from mag.conductor import conduct

    res = conduct("[build] implement frozen spec on branch", dry=True)
    assert res.get("overlay", {}).get("skill_seat") in ("ponytail", "caveman", None)
