"""Orchestrator training hooks + grove REST (v3 DeepSeek run wiring)."""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_emit_task_lifecycle_on_finalize(tmp_path, monkeypatch):
    from mag import orchestrator as orc
    from mag import training_events as te

    orc.TASK_DIR = tmp_path / "tasks"
    orc.TRAIL = tmp_path / "trail.jsonl"
    orc.TASK_DIR.mkdir(parents=True)
    monkeypatch.setattr(te, "EVENTS_PATH", tmp_path / "events.jsonl")

    tid = "t" + uuid.uuid4().hex[:10]
    orc._save({
        "task_id": tid,
        "status": "running",
        "goal": "test lifecycle goal",
        "provider": "deepseek",
        "cmd": [sys.executable, "main.py", "agent", "--query", "x", "--provider", "deepseek"],
        "created_at": orc._now(),
    })
    orc._finalize(tid, "done", exit_code=0, detail="exit")

    rows = te.read_events(pattern="task_lifecycle")
    assert any(r.get("join", {}).get("task_id") == tid for r in rows)
    hit = next(r for r in rows if r.get("join", {}).get("task_id") == tid)
    assert hit.get("action", {}).get("phase") == "done"


def test_grove_rest_handler(tmp_path, monkeypatch):
    from mag import grove
    from dashboard.rest import h_grove

    monkeypatch.setattr(grove, "GROVE_ROOT", tmp_path / "grove")
    monkeypatch.setattr(grove, "NODES_DIR", tmp_path / "grove" / "nodes")
    monkeypatch.setattr(grove, "INDEX_PATH", tmp_path / "grove" / "index.jsonl")
    grove.NODES_DIR.mkdir(parents=True)
    node = {
        "schema": "grove_node.v1",
        "id": "grove-test-1",
        "kind": "skill",
        "title": "test",
        "poem": "file first;",
    }
    (grove.NODES_DIR / "grove-test-1.json").write_text(json.dumps(node), encoding="utf-8")

    code, body = h_grove({"limit": "10"}, None)
    assert code == 200
    assert body.get("ok") is True
    assert body.get("count", 0) >= 1
    assert any(n.get("id") == "grove-test-1" for n in body.get("nodes") or [])


def test_autorun_rest_handler():
    from dashboard.rest import h_autorun

    code, body = h_autorun({}, None)
    assert code == 200
    assert body.get("ok") is True
    assert body.get("schema") == "autorun_status.v1"
    assert "governor" in body
    assert "autorun" in body


def test_handoff_inbox_rest_handler():
    from dashboard.rest import h_handoff_inbox

    code, body = h_handoff_inbox({"limit": "5"}, None)
    assert code == 200
    assert body.get("ok") is True
    assert body.get("schema") == "handoff_inbox.v1"
