"""Queue lanes: operator work drains before test/autopilot noise."""

from __future__ import annotations

import json
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mag import orchestrator as orc


def _fake_spawn(goal, *, provider="deepseek", model=None, timeout=900, tag=""):
    tid = "t" + uuid.uuid4().hex[:10]
    return {
        "ok": True,
        "task_id": tid,
        "goal": goal,
        "status": "running",
        "provider": provider,
        "tag": tag,
    }


@pytest.fixture
def isolated_queue(tmp_path, monkeypatch):
    qdir = tmp_path / "queue"
    tdir = tmp_path / "tasks"
    qdir.mkdir()
    tdir.mkdir()
    events = tmp_path / "behavioral_events.jsonl"
    monkeypatch.setattr(orc, "QUEUE_DIR", qdir)
    monkeypatch.setattr(orc, "TASK_DIR", tdir)
    monkeypatch.setattr(orc, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(orc, "spawn_task", _fake_spawn)
    import mag.operator_inbox as inbox

    monkeypatch.setattr(inbox, "EVENTS_PATH", events)
    yield qdir, events


def test_infer_lane():
    assert orc.infer_lane(goal="[test] three-track smoke", tag="api") == "test"
    assert orc.infer_lane(tag="epic-scut", goal="doctor status") == "operator"
    assert orc.infer_lane(tag="autopilot-simple_code", goal="[attention] pdf") == "autopilot"
    assert orc.infer_lane(provider="ollama", tag="x", goal="brief bonds") == "scut"


def test_drain_prefers_operator_over_test(isolated_queue):
    qdir, events = isolated_queue
    orc.enqueue("[test] smoke item", tag="api", lane="test")
    orc.enqueue("real operator goal", tag="epic-scut", lane="operator")

    r = orc.drain_once()
    assert r.get("action") == "started"
    assert r.get("lane") == "operator"
    assert "operator" in r.get("goal", "")

    assert events.is_file()
    kinds = [json.loads(line)["kind"] for line in events.read_text(encoding="utf-8").splitlines()]
    assert "queue_enqueue" in kinds
    assert "queue_started" in kinds


def test_drain_skips_test_lane_by_default(isolated_queue):
    isolated_queue
    orc.enqueue("[test] only test", tag="api", lane="test")
    r = orc.drain_once()
    assert r.get("action") == "empty"

    r2 = orc.drain_once(include_test=True)
    assert r2.get("action") == "started"
    assert r2.get("lane") == "test"


def test_queue_status_by_lane(isolated_queue):
    isolated_queue
    orc.enqueue("op", lane="operator")
    orc.enqueue("[test] x", lane="test")
    st = orc.queue_status()
    assert st["by_lane"]["operator"]["queued"] == 1
    assert st["by_lane"]["test"]["queued"] == 1
