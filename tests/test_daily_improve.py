"""Daily improve orchestrator scheduling."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from mag.daily_improve import (
    DAILY_GOAL,
    DAILY_TAG,
    is_daily_improve_due,
    maybe_schedule_daily_improve,
    run_daily_improve,
)


@pytest.fixture
def improve_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    imp = tmp_path / "memory" / "improve"
    imp.mkdir(parents=True)
    (imp / "state.json").write_text("{}", encoding="utf-8")
    (imp / "candidates.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "runs" / "orchestrator" / "queue").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    import config
    import mag.daily_improve as daily
    import mag.improve as imp_mod
    import mag.orchestrator as orch
    import mag.preferences as prefs

    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(imp_mod, "ROOT", tmp_path)
    monkeypatch.setattr(orch, "ROOT", tmp_path)
    monkeypatch.setattr(daily, "ROOT", tmp_path)
    monkeypatch.setattr(prefs, "ROOT", tmp_path)
    monkeypatch.setattr(prefs, "PREF_PATH", tmp_path / "state" / "mag_preferences.json")
    monkeypatch.setattr(daily, "SCHEDULE_STATE", tmp_path / "state" / "daily_improve.json")
    return tmp_path


def test_improve_daily_enabled_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import mag.preferences as prefs

    monkeypatch.setattr(prefs, "PREF_PATH", tmp_path / "state" / "mag_preferences.json")
    monkeypatch.delenv("MAG_IMPROVE_DAILY", raising=False)
    assert prefs.improve_daily_enabled() is True


def test_is_daily_improve_due_respects_hour(improve_root: Path, monkeypatch: pytest.MonkeyPatch):
    tz = ZoneInfo("America/New_York")
    early = datetime(2026, 8, 5, 7, 30, tzinfo=tz)
    late = datetime(2026, 8, 5, 8, 15, tzinfo=tz)

    with patch("mag.daily_improve.datetime") as mock_dt:
        mock_dt.now.return_value = early
        assert is_daily_improve_due() is False

    with patch("mag.daily_improve.datetime") as mock_dt:
        mock_dt.now.return_value = late
        assert is_daily_improve_due() is True


def test_maybe_schedule_enqueues_daily_job(improve_root: Path, monkeypatch: pytest.MonkeyPatch):
    tz = ZoneInfo("America/New_York")
    late = datetime(2026, 8, 5, 8, 30, tzinfo=tz)

    with patch("mag.daily_improve.datetime") as mock_dt:
        mock_dt.now.return_value = late
        rec = maybe_schedule_daily_improve()
    assert rec is not None
    assert rec.get("tag") == DAILY_TAG or rec.get("queue_id")

    with patch("mag.daily_improve.datetime") as mock_dt:
        mock_dt.now.return_value = late
        again = maybe_schedule_daily_improve()
    assert again is None


def test_spawn_task_mag_cmd(monkeypatch: pytest.MonkeyPatch):
    import mag.orchestrator as orch

    captured: dict = {}

    def fake_spawn(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return {"task_id": kwargs.get("task_id", "t-test"), "status": "running"}

    monkeypatch.setattr(orch, "_spawn_cmd", fake_spawn)
    rec = orch.spawn_task("[mag-cmd] daily-improve", tag="MagImproveDaily")
    assert rec.get("ok") is True
    assert rec.get("kind") == "mag-cmd"
    cmd = captured["cmd"]
    assert "daily-improve" in cmd
    assert cmd[-1] == "daily-improve"


def test_run_daily_improve_queues_deepseek(improve_root: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "mag.improve.improve_once",
        lambda **_: {"ok": True, "field_brief": "memory/improve/field_brief.md"},
    )
    monkeypatch.setattr(
        "mag.autopilot._top_improve_candidates",
        lambda limit=3: [
            {"id": "c-abc123", "claim": "Test practice ticket", "score": 15},
        ],
    )
    enqueued: list[str] = []

    def fake_enqueue(goal, **kwargs):
        enqueued.append(goal)
        return {"queue_id": "q-test", "goal": goal, **kwargs}

    monkeypatch.setattr("mag.orchestrator.enqueue", fake_enqueue)
    res = run_daily_improve(max_queue=1)
    assert res.get("ok") is True
    assert enqueued
    assert enqueued[0].startswith("[improve]")
