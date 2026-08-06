"""TextArena arena adapter — MagSeatAgent, run_probe, probe_type telemetry."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mag import arena_adapter as aa
from mag import arena_learning as al


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    profiles = tmp_path / "arena_profiles.jsonl"
    league = tmp_path / "arena_league.json"
    trail = tmp_path / "arena_trail.jsonl"
    state = tmp_path / "arena_probe.json"
    monkeypatch.setattr(al, "PROFILES_PATH", profiles)
    monkeypatch.setattr(al, "LEAGUE_PATH", league)
    monkeypatch.setattr(al, "TRAIL", trail)
    monkeypatch.setattr(aa, "STATE_PATH", state)
    yield


def test_list_games_from_yaml():
    out = aa.list_games()
    assert out["ok"] is True
    assert out["n"] >= 1
    ids = {g["game_id"] for g in out["games"]}
    assert "TicTacToe-v0" in ids


def test_probe_meta():
    meta = aa.probe_meta("TicTacToe-v0")
    assert meta["probe_type"] == "structured_handoff"
    assert meta["routing_task"] == "schema"


def test_record_move_probe_type_and_messages():
    row = al.record_move(
        seat="local",
        game="TicTacToe-v0",
        ok=True,
        move="5",
        game_id="probe-test1",
        messages=["obs", "5"],
        probe_type="structured_handoff",
        timing_ms=42,
    )
    assert row["probe_type"] == "structured_handoff"
    assert row["messages"] == ["obs", "5"]
    assert row["timing_ms"] == 42


def test_routing_hint_filters_probe_type():
    al.record_move(
        seat="local",
        game="TicTacToe-v0",
        ok=True,
        move="1",
        probe_type="structured_handoff",
        game_id="g1",
    )
    al.record_game_end(
        game="TicTacToe-v0",
        white="local",
        black="remote",
        status="finished",
        winner="local",
        moves=3,
        game_id="g1",
        probe_type="structured_handoff",
    )
    hint = al.routing_hint(probe_type="structured_handoff", league=al.rebuild_league(game="TicTacToe-v0", probe_type="structured_handoff").get("rankings"))
    assert hint.get("probe_type") == "structured_handoff"
    assert hint.get("recommend") in ("local", "remote")


def test_mag_seat_agent_random(monkeypatch):
    monkeypatch.setenv("MAG_ARENA_RANDOM", "1")
    agent = aa.MagSeatAgent("local")
    action = agent("Pick one: [3] [5] [7]")
    assert action in ("3", "5", "7")
    assert agent.last_messages


class _FakeEnv:
    def __init__(self):
        self._step = 0

    def reset(self, num_players=2):
        self._step = 0

    def get_observation(self):
        return 0 if self._step == 0 else 1, "Pick: [1] [2] [3]"

    def step(self, action="1"):
        self._step += 1
        done = self._step >= 2
        return done, {"invalid": False}

    def close(self):
        return {0: 1.0, 1: 0.0}, {"status": "done"}


def test_run_probe_mocked_textarena(monkeypatch):
    fake_ta = SimpleNamespace(
        make=lambda env_id: _FakeEnv(),
        wrappers=SimpleNamespace(
            SimpleRenderWrapper=lambda env, player_names=None: env,
            LLMObservationWrapper=lambda env: env,
        ),
    )
    monkeypatch.setattr(aa, "ta", fake_ta)
    monkeypatch.setattr(aa, "_HAS_TEXTARENA", True)
    monkeypatch.setenv("MAG_ARENA_RANDOM", "1")

    out = aa.run_probe(game_id="TicTacToe-v0", seats=["local", "remote"])
    assert out["ok"] is True
    assert out["probe"]["probe_type"] == "structured_handoff"
    assert len(out["message_log"]) >= 1

    rows = al._read_profile_rows(game="TicTacToe-v0")
    move_rows = [r for r in rows if r.get("kind") == "move"]
    assert move_rows
    assert move_rows[0].get("probe_type") == "structured_handoff"
    assert move_rows[0].get("messages")


def test_handle_action_probe_delegates(monkeypatch):
    from mag import agent_arena

    monkeypatch.setattr(
        aa,
        "run_probe",
        lambda **kw: {"ok": True, "probe": {"game": kw.get("game_id")}, "message_log": []},
    )
    monkeypatch.setattr(aa, "_HAS_TEXTARENA", True)
    out = agent_arena.handle_action({"action": "probe", "game_id": "TicTacToe-v0"})
    assert out["ok"] is True
    assert out["probe"]["game"] == "TicTacToe-v0"


def test_handle_action_list_games():
    from mag import agent_arena

    out = agent_arena.handle_action({"action": "list_games"})
    assert out["ok"] is True
    assert out["n"] >= 1
