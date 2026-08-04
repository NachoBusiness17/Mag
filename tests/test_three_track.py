"""Three-track surface: workspace_api + autopilot + orchestrator queue REST."""
from __future__ import annotations

from pathlib import Path

import pytest

from config import ROOT
from mag.autopilot import autopilot_once
from mag.workspace_api import list_tree, read_file, write_file


def test_workspace_rejects_traversal():
    assert list_tree("../etc")["ok"] is False
    assert read_file("../../outside.txt")["ok"] is False


def test_workspace_list_and_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    rel = "tests/_shell_scratch"
    base = ROOT / rel
    base.mkdir(parents=True, exist_ok=True)
    target = base / "hello.txt"
    try:
        wrote = write_file(f"{rel}/hello.txt", "shell test\n")
        assert wrote["ok"] is True

        tree = list_tree(rel, max_depth=1)
        assert tree["ok"] is True
        assert any(e["name"] == "hello.txt" for e in tree["entries"])

        got = read_file(f"{rel}/hello.txt")
        assert got["ok"] is True
        assert "shell test" in got["text"]
    finally:
        if target.is_file():
            target.unlink()
        if base.is_dir() and not any(base.iterdir()):
            base.rmdir()


def test_autopilot_once_shape():
    res = autopilot_once(queue_improve=False, governor=False, drain=False)
    assert res.get("ok") is True
    assert res.get("schema") == "autopilot.v1"
    assert "seed_mirror" in res
    assert isinstance(res.get("steps"), list)


def test_orchestrator_queue_handler():
    from dashboard.rest import h_orchestrator_queue_post

    code, body = h_orchestrator_queue_post({}, None)
    assert code == 400

    code, body = h_orchestrator_queue_post({}, {"goal": "[test] three-track smoke"})
    assert code == 200
    assert body.get("ok") is True
    assert body.get("queue_id") or body.get("goal")


def test_seat_task_routes_modes():
    from dashboard.rest import h_seat_task

    code, body = h_seat_task({}, None)
    assert code == 400

    code, body = h_seat_task({}, {"mode": "nope", "goal": "x"})
    assert code == 400
    assert "unknown mode" in str(body.get("error") or "")

    code, body = h_seat_task({}, {"mode": "queue", "goal": "[test] seat task queue"})
    assert code == 200
    assert body.get("ok") is True
    assert body.get("mode") == "queue"
    assert body.get("seat") == "cursor"

    code, body = h_seat_task({}, {"mode": "autopilot", "seat": "cursor"})
    assert code == 200
    assert body.get("ok") is True
    assert body.get("mode") == "autopilot"
