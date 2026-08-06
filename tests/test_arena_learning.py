"""Arena learning loop — profiles, league, nervous/switchboard hooks."""
from __future__ import annotations

import json

import pytest

from mag import agent_arena as arena
from mag import arena_learning as al


@pytest.fixture(autouse=True)
def _isolated_arena_learning(tmp_path, monkeypatch):
    state_path = tmp_path / "agent_arena.json"
    profiles = tmp_path / "arena_profiles.jsonl"
    league = tmp_path / "arena_league.json"
    trail = tmp_path / "arena_trail.jsonl"
    events = tmp_path / "events.jsonl"
    monkeypatch.setattr(arena, "STATE_PATH", state_path)
    monkeypatch.setattr(al, "PROFILES_PATH", profiles)
    monkeypatch.setattr(al, "LEAGUE_PATH", league)
    monkeypatch.setattr(al, "TRAIL", trail)
    yield


def test_record_move_and_game_end():
    al.record_move(seat="local", ok=True, move="e4", game_id="arena-test1")
    al.record_move(seat="local", ok=False, move="Qh5", illegal=True, game_id="arena-test1")
    rec = al.record_game_end(
        game="chess",
        white="local",
        black="remote",
        status="checkmate",
        winner="local",
        moves=12,
        game_id="arena-test1",
    )
    assert rec["ok"] is True
    league = rec["league"]
    assert league.get("n_seats") >= 1
    ranks = league.get("rankings") or []
    local = next((r for r in ranks if r.get("seat") == "local"), None)
    assert local is not None
    assert local["wins"] >= 1
    assert local["illegal_moves"] >= 1


def test_ingest_dedupes_game():
    state = {
        "game_id": "arena-dup",
        "game": "chess",
        "white": "local",
        "black": "remote",
        "status": "draw",
        "winner": None,
        "move_history": [{"san": "e4"}],
    }
    first = al.ingest_arena_state(state)
    second = al.ingest_arena_state(state)
    assert first is not None
    assert second is None


def test_routing_hint_default_without_data():
    hint = al.routing_hint(budget="low", league=[])
    assert hint["recommend"] == "local"
    assert "no arena data" in hint["reason"]


@pytest.mark.skipif(not arena._HAS_CHESS, reason="python-chess not installed")
def test_apply_move_feeds_learning(monkeypatch):
    arena.new_game(white="local", black="remote")
    bad = arena.apply_move("Qh5", seat="local")
    assert bad["ok"] is False
    good = arena.apply_move("e4", seat="local")
    assert good["ok"] is True
    rows = al._read_profile_rows()
    kinds = [r.get("kind") for r in rows]
    assert "move" in kinds


@pytest.mark.skipif(not arena._HAS_CHESS, reason="python-chess not installed")
def test_tournament_random(monkeypatch):
    monkeypatch.setenv("MAG_ARENA_RANDOM", "1")
    out = al.run_tournament(rounds=1, seats=("local", "remote"))
    assert out["ok"] is True
    assert out.get("games", 0) >= 0
    league = out.get("league") or {}
    assert "rankings" in league


def test_nervous_glance_shape():
    g = al.nervous_glance()
    assert g.get("schema") == al.SCHEMA
    assert "routing_hint" in g
