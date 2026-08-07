"""Agent arena — chess POC tests."""
from __future__ import annotations

import pytest

from mag import agent_arena as arena


@pytest.fixture(autouse=True)
def _clean_arena_state(tmp_path, monkeypatch):
    state_path = tmp_path / "agent_arena.json"
    monkeypatch.setattr(arena, "STATE_PATH", state_path)
    yield
    if state_path.is_file():
        state_path.unlink()


@pytest.mark.skipif(not arena._HAS_CHESS, reason="python-chess not installed")
def test_new_game_and_move():
    out = arena.new_game(white="local", black="remote")
    assert out["ok"] is True
    assert out["active"] is True
    assert out["turn_seat"] == "local"
    assert len(out["board"]) == 8

    moved = arena.apply_move("e4", seat="local")
    assert moved["ok"] is True
    assert moved["applied"] == "e4"
    assert moved["turn_seat"] == "remote"
    assert moved["last_move"]["uci"] == "e2e4"


@pytest.mark.skipif(not arena._HAS_CHESS, reason="python-chess not installed")
def test_agent_turn_random(monkeypatch):
    monkeypatch.setenv("MAG_ARENA_RANDOM", "1")
    arena.new_game()
    turn = arena.agent_turn(seat="local")
    assert turn["ok"] is True
    assert turn.get("applied")
    assert turn["agent_seat"] == "local"


@pytest.mark.skipif(not arena._HAS_CHESS, reason="python-chess not installed")
def test_handle_action_play(monkeypatch):
    monkeypatch.setenv("MAG_ARENA_RANDOM", "1")
    arena.handle_action({"action": "new"})
    out = arena.handle_action({"action": "play"})
    assert out["ok"] is True
    assert isinstance(out.get("moves"), list)
    assert out["state"]["active"] is True


def test_status_idle():
    out = arena.status()
    assert out["ok"] is True
    assert out["active"] is False
    assert "chess" in out.get("supported", [])


@pytest.mark.skipif(not arena._HAS_CHESS, reason="python-chess not installed")
def test_illegal_move():
    arena.new_game()
    bad = arena.apply_move("Qh5")
    assert bad["ok"] is False
    assert "illegal" in bad["error"].lower()
