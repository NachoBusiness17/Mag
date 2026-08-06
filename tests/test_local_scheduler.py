"""Local GPU scheduler tests."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag import local_scheduler as ls


def test_steer_pause_continue(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "STATE_PATH", tmp_path / "sched.json")
    ls.steer("!pause")
    s = ls.status()
    assert s["paused"] is True
    ls.steer("!continue")
    assert ls.status()["paused"] is False


def test_enqueue_priority_sort(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "STATE_PATH", tmp_path / "sched.json")
    monkeypatch.setattr(ls, "deepseek_triage", lambda **kw: {"ok": True, "skipped": True})
    a = ls.enqueue(kind="desk", payload={"slow_wake": True}, priority=5, label="low")
    b = ls.enqueue(kind="desk", payload={"operator_note": "urgent"}, priority=10, label="high")
    s = ls.status()
    assert s["pending"][0]["id"] == b["task_id"]


def test_run_exclusive_bypass(monkeypatch):
    monkeypatch.setenv("MAG_LOCAL_SCHEDULER", "0")
    out = ls.run_exclusive(kind="test", payload={"x": 1}, executor=lambda p: {"ok": True, "x": p["x"]})
    assert out["ok"] is True
    assert out["x"] == 1


def test_h_local_scheduler_get():
    from dashboard.rest import h_local_scheduler

    code, body = h_local_scheduler({}, None)
    assert code == 200
    assert body.get("schema") == ls.SCHEMA
