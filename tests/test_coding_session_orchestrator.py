"""Coding session orchestrator — PO/SM planning (no LLM)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag.coding_session_loop import CONFIG_PATH, load_config, seed_desk  # noqa: E402
from mag.coding_session_orchestrator import (  # noqa: E402
    ORCH_STATE_PATH,
    active_sprint_key,
    assess_sprint_status,
    plan_session,
    recommend_desk_action,
)


def test_active_sprint_defaults_to_first_in_config(tmp_path, monkeypatch):
    orch_state = tmp_path / "orch.json"
    monkeypatch.setattr("mag.coding_session_orchestrator.ORCH_STATE_PATH", orch_state)
    monkeypatch.setattr(
        "mag.coding_session_orchestrator._sprint_gate_check",
        lambda c, k: {"sprint": k, "pass": False, "reason": "mock"},
    )
    cfg = load_config(CONFIG_PATH)
    cfg.pop("current_sprint", None)
    assert active_sprint_key(config=cfg) == "sprint_0_preflight"


def test_assess_sprint_status_structure(tmp_path, monkeypatch):
    orch_state = tmp_path / "orch.json"
    monkeypatch.setattr("mag.coding_session_orchestrator.ORCH_STATE_PATH", orch_state)
    monkeypatch.setattr(
        "mag.coding_session_orchestrator._sprint_gate_check",
        lambda c, k: {"sprint": k, "pass": False, "reason": "mock"},
    )
    cfg = load_config(CONFIG_PATH)
    cfg.pop("current_sprint", None)
    out = assess_sprint_status(config=cfg)
    assert out.get("ok")
    assert out.get("active_sprint") == "sprint_0_preflight"
    assert isinstance(out.get("sprint_checks"), list)
    assert len(out.get("sprint_checks") or []) >= 4


def test_recommend_desk_action_preflight():
    cfg = load_config(CONFIG_PATH)
    status = {
        "active_sprint": "sprint_0_preflight",
        "done_when": "all preflight gates pass",
        "sprint_checks": [{"sprint": "sprint_0_preflight", "pass": False}],
    }
    action = recommend_desk_action(status=status, config=cfg)
    assert "preflight" in action.lower() or "step" in action.lower()


def test_plan_session_writes_knowns_unknowns(tmp_path, monkeypatch):
    desk = tmp_path / "agent_desk.md"
    cursor = tmp_path / "agent_desk_cursor.json"
    orch_state = tmp_path / "coding_session_orchestrator.json"
    monkeypatch.setattr("mag.agent_desk.DESK_PATH", desk)
    monkeypatch.setattr("mag.agent_desk.ROOT", tmp_path)
    monkeypatch.setattr("mag.coding_session_orchestrator.ORCH_STATE_PATH", orch_state)
    monkeypatch.setattr(
        "mag.coding_session_orchestrator._sprint_gate_check",
        lambda c, k: {"sprint": k, "pass": False, "reason": "mock"},
    )
    cfg = load_config(CONFIG_PATH)
    cfg.pop("current_sprint", None)
    out = plan_session(config=cfg)
    assert out.get("ok")
    assert out.get("knowns")
    assert out.get("unknowns")
    assert orch_state.is_file()
    text = desk.read_text(encoding="utf-8")
    assert "## Knowns" in text
    assert "## Unknowns" in text
    assert "## Current sprint" in text
    assert out.get("active_sprint") == "sprint_0_preflight"
    assert "build_audit" in text.lower() or "factory" in text.lower()


def test_seed_desk_includes_orchestrator_sections(tmp_path, monkeypatch):
    desk = tmp_path / "agent_desk.md"
    cursor = tmp_path / "agent_desk_cursor.json"
    state = tmp_path / "coding_session_loop.json"
    dialogue = tmp_path / "agent_desk_dialogue.jsonl"
    orch_state = tmp_path / "coding_session_orchestrator.json"
    monkeypatch.setattr("mag.agent_desk.DESK_PATH", desk)
    monkeypatch.setattr("mag.agent_desk.ROOT", tmp_path)
    monkeypatch.setattr("mag.desk_dialogue.CURSOR_PATH", cursor)
    monkeypatch.setattr("mag.desk_dialogue.DIALOGUE_LOG", dialogue)
    monkeypatch.setattr("mag.coding_session_loop.SESSION_STATE_PATH", state)
    monkeypatch.setattr("mag.coding_session_orchestrator.ORCH_STATE_PATH", orch_state)
    monkeypatch.setattr(
        "mag.coding_session_orchestrator._sprint_gate_check",
        lambda c, k: {"sprint": k, "pass": False, "reason": "mock"},
    )
    cfg = load_config(CONFIG_PATH)
    out = seed_desk(config=cfg)
    assert out.get("ok")
    text = desk.read_text(encoding="utf-8")
    assert "## Knowns" in text
    assert "## Unknowns" in text
    assert "## Current sprint" in text
    assert "## Conductor scratch" in text
    assert "Active sprint" in text or "sprint_0" in text
