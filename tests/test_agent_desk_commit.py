"""Tests for canvas-first commit helpers."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag.agent_desk import (  # noqa: E402
    DESK_PATH,
    commit_operator_intent,
    read_desk,
    set_desk_goal,
    write_desk,
)


def test_set_desk_goal_replaces_section(tmp_path, monkeypatch):
    monkeypatch.setattr("mag.agent_desk.DESK_PATH", tmp_path / "agent_desk.md")
    monkeypatch.setattr("mag.agent_desk.ROOT", tmp_path)
    write_desk("## Goal\n(old)\n\n## Dialogue\n\n")
    set_desk_goal("Ship build_audit.v1 JSON.")
    text = read_desk()["text"]
    assert "Ship build_audit.v1 JSON." in text
    assert "(old)" not in text
    assert "## Dialogue" in text


def test_commit_operator_intent_goal_and_note(tmp_path, monkeypatch):
    monkeypatch.setattr("mag.agent_desk.DESK_PATH", tmp_path / "agent_desk.md")
    monkeypatch.setattr("mag.agent_desk.ROOT", tmp_path)
    write_desk("## Goal\n\n## Operator notes\n\n")
    out = commit_operator_intent(goal="Factory pilot gate.", note="Start with preflight.")
    assert out.get("ok") is not False
    assert "goal" in out.get("committed", [])
    assert "operator_note" in out.get("committed", [])
    text = read_desk()["text"]
    assert "Factory pilot gate." in text
    assert "Start with preflight." in text


def test_commit_empty_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr("mag.agent_desk.DESK_PATH", tmp_path / "agent_desk.md")
    monkeypatch.setattr("mag.agent_desk.ROOT", tmp_path)
    write_desk("## Goal\nkeep\n")
    before = read_desk()["text"]
    commit_operator_intent()
    assert read_desk()["text"] == before
