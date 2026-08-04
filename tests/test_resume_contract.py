"""Resume contract: seat writes state/CURRENT.md; task hint reads it authoritatively.

The seat (mag.agent_cli._sync_current) mirrors its live state into the same
state/CURRENT.md contract the router pipeline writes, so a fresh seat / the
router / the operator reads ONE small file to know where things stand instead
of re-reading the whole weave. _current_task_hint() reads the ## Goal field
first (authoritative), falling back to prose-scan only if absent.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mag import agent_cli
from mag import operator_inbox as inbox


@pytest.fixture(autouse=True)
def _isolate_current(tmp_path, monkeypatch):
    """Point state/CURRENT.md at a temp path so tests never touch the real one."""
    cur = tmp_path / "state" / "CURRENT.md"
    monkeypatch.setattr(agent_cli, "ROOT", tmp_path)
    # operator_inbox reads ROOT/state/CURRENT.md too
    monkeypatch.setattr(inbox, "ROOT", tmp_path)
    # audit.sync_current writes config.CURRENT_MD - redirect it to the temp path
    import audit
    import config
    monkeypatch.setattr(config, "CURRENT_MD", cur)
    monkeypatch.setattr(audit, "CURRENT_MD", cur)
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    yield cur


def test_sync_current_writes_contract(tmp_path):
    agent_cli._activity = {"step": 3, "last_tool": "read_file", "phase": "working", "goal": "test goal"}
    agent_cli._sync_current(
        goal="test goal",
        plan=["step1", "step2"],
        last_result="some result",
        status="running",
    )
    cur = tmp_path / "state" / "CURRENT.md"
    assert cur.is_file()
    txt = cur.read_text(encoding="utf-8")
    assert "test goal" in txt
    assert "**status:** running" in txt
    assert "**step_i:** 3" in txt
    assert "step1" in txt


def test_sync_current_never_raises(tmp_path):
    # Even if audit.sync_current fails (e.g. bad state), the seat must survive.
    agent_cli._activity = {"step": 0, "last_tool": "-", "phase": "starting"}
    agent_cli._sync_current(goal="x", status="running")  # should not raise
    assert True


def test_current_task_hint_reads_goal_authoritatively(tmp_path):
    (tmp_path / "state" / "CURRENT.md").write_text(
        "# CURRENT\n\n- **status:** running\n\n## Goal\n\nBuild the resume contract\n\n## Plan\n\n- step1\n",
        encoding="utf-8",
    )
    hint = inbox._current_task_hint()
    assert hint == "Build the resume contract"


def test_current_task_hint_falls_back_to_prose_when_absent(tmp_path):
    # No state/CURRENT.md -> falls back to scanning working.md prose.
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "working.md").write_text(
        "# Working\n\n- first bullet task\n- second bullet\n",
        encoding="utf-8",
    )
    hint = inbox._current_task_hint()
    # pre-existing fallback keeps the "- " bullet prefix
    assert hint == "- first bullet task"


def test_current_task_hint_default_when_nothing(tmp_path):
    hint = inbox._current_task_hint()
    assert hint == "active agent turn"
