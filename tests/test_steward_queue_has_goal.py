"""Steward imports queue_has_goal from the right module (dinner-loop fix)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_queue_has_goal_importable_from_orchestrator():
    from mag.orchestrator import queue_has_goal

    assert callable(queue_has_goal)
    assert queue_has_goal("") is False


def test_queue_has_goal_importable_from_governor_autorun():
    from mag.governor_autorun import queue_has_goal

    assert callable(queue_has_goal)


def test_steward_fill_does_not_import_error(monkeypatch):
    """fill_steward_queue must not raise ImportError on queue_has_goal."""
    from mag import steward

    monkeypatch.setattr(steward, "find_frozen_builds", lambda: [])
    monkeypatch.setattr(steward, "ran_today", lambda _j: True)
    # daily already "ran" so no candidates — still must import cleanly
    out = steward.fill_steward_queue(max_jobs=0)
    assert isinstance(out, list)


def test_republic_in_fs_roots_when_present():
    from config import FS_ROOTS, ROOT

    names = [p.name for p in FS_ROOTS]
    assert ROOT.name in names or any(p == ROOT for p in FS_ROOTS)
    # sibling may or may not exist on all CI machines
    rep = ROOT.parent / "mycelial-republic"
    if rep.is_dir():
        assert any(p.resolve() == rep.resolve() for p in FS_ROOTS)
