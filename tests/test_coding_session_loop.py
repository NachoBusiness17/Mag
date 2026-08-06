"""Coding session loop config + seed."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag.coding_session_loop import (  # noqa: E402
    CONFIG_PATH,
    SESSION_STATE_PATH,
    close_session_if_ready,
    load_config,
    run_preflight,
    seed_desk,
)


def test_load_config_has_session_id():
    cfg = load_config(CONFIG_PATH)
    assert cfg.get("ok")
    assert cfg.get("session_id") == "beta1-factory-build-audit-001"
    assert cfg.get("playbook") == "code_scout_janitor"


def test_seed_desk_writes_goal(tmp_path, monkeypatch):
    desk = tmp_path / "agent_desk.md"
    cursor = tmp_path / "agent_desk_cursor.json"
    state = tmp_path / "coding_session_loop.json"
    dialogue = tmp_path / "agent_desk_dialogue.jsonl"
    monkeypatch.setattr("mag.agent_desk.DESK_PATH", desk)
    monkeypatch.setattr("mag.agent_desk.ROOT", tmp_path)
    monkeypatch.setattr("mag.desk_dialogue.CURSOR_PATH", cursor)
    monkeypatch.setattr("mag.desk_dialogue.DIALOGUE_LOG", dialogue)
    monkeypatch.setattr("mag.coding_session_loop.SESSION_STATE_PATH", state)
    cfg = load_config(CONFIG_PATH)
    out = seed_desk(config=cfg)
    assert out.get("ok")
    text = desk.read_text(encoding="utf-8")
    assert "## Goal" in text
    assert "build_audit" in text
    assert "## Knowns" in text
    assert "## Unknowns" in text
    assert "## Current sprint" in text
    assert state.is_file()
    cur = json.loads(cursor.read_text(encoding="utf-8"))
    assert cur.get("holder") == "operator"
    assert cur.get("wake_pending") is False


def test_preflight_unit_gates_pass():
    cfg = load_config(CONFIG_PATH)
    # Drop optional ui_smoke for offline CI
    gates = cfg.get("gates") or {}
    pre = [g for g in gates.get("preflight") or [] if g.get("id") != "ui_smoke"]
    cfg["gates"] = {"preflight": pre}
    out = run_preflight(config=cfg)
    assert out.get("ok"), out.get("preflight")


def test_close_session_if_ready_gates_open(tmp_path, monkeypatch):
    desk = tmp_path / "agent_desk.md"
    state = tmp_path / "coding_session_loop.json"
    gates_log = tmp_path / "memory" / "improve" / "releases" / "gates.jsonl"
    monkeypatch.setattr("mag.agent_desk.DESK_PATH", desk)
    monkeypatch.setattr("mag.agent_desk.ROOT", tmp_path)
    monkeypatch.setattr("mag.coding_session_loop.SESSION_STATE_PATH", state)
    monkeypatch.setattr("mag.release_registry.GATES_LOG", gates_log)
    monkeypatch.setattr(
        "mag.coding_session_loop._run_cmd",
        lambda cmd, optional=False: {"ok": False, "pass": False, "cmd": cmd, "optional": optional},
    )
    monkeypatch.setattr(
        "mag.coding_session_loop._check_path_gate",
        lambda spec: {"id": spec.get("id"), "pass": False},
    )
    cfg = load_config(CONFIG_PATH)
    out = close_session_if_ready(config=cfg)
    assert out.get("ok")
    assert out.get("closed") is False
    assert out.get("reason") == "session_done_gates_open"


def test_close_session_if_ready_closes_when_green(tmp_path, monkeypatch):
    desk = tmp_path / "agent_desk.md"
    desk.write_text("# Agent desk\n\n## Goal\nx\n", encoding="utf-8")
    state = tmp_path / "coding_session_loop.json"
    state.write_text(
        json.dumps({"schema": "coding_session_loop.v1", "status": "ready", "session_id": "test-session"}),
        encoding="utf-8",
    )
    gates_log = tmp_path / "memory" / "improve" / "releases" / "gates.jsonl"
    events = tmp_path / "memory" / "training" / "events.jsonl"
    gates_log.parent.mkdir(parents=True, exist_ok=True)
    events.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("mag.agent_desk.DESK_PATH", desk)
    monkeypatch.setattr("mag.agent_desk.ROOT", tmp_path)
    monkeypatch.setattr("mag.coding_session_loop.SESSION_STATE_PATH", state)
    monkeypatch.setattr("mag.release_registry.GATES_LOG", gates_log)
    monkeypatch.setattr("mag.training_events.EVENTS_PATH", events)
    monkeypatch.setattr(
        "mag.coding_session_loop._run_cmd",
        lambda cmd, optional=False: {"ok": True, "pass": True, "cmd": cmd, "optional": optional},
    )
    monkeypatch.setattr(
        "mag.coding_session_loop._check_path_gate",
        lambda spec: {"id": spec.get("id"), "pass": True},
    )
    monkeypatch.setattr(
        "mag.run_trail.close_run",
        lambda reason="done": {"ok": True, "reason": reason},
    )

    cfg = dict(load_config(CONFIG_PATH))
    cfg["session_id"] = "test-session"
    cfg["bead_on_close"] = False
    out = close_session_if_ready(config=cfg)
    assert out.get("ok")
    assert out.get("closed") is True
    assert out.get("done_written") is True
    text = desk.read_text(encoding="utf-8")
    assert "## Done" in text
    st = json.loads(state.read_text(encoding="utf-8"))
    assert st.get("status") == "closed"
