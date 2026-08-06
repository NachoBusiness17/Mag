"""Training events — unified orchestration label capture."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_emit_and_read(tmp_path, monkeypatch):
    from mag import training_events as te

    monkeypatch.setattr(te, "EVENTS_PATH", tmp_path / "events.jsonl")
    row = te.emit(
        "route_decision",
        input_data={"goal": "test goal"},
        action={"seat": "local"},
        pattern_tags=["test"],
    )
    assert row.get("schema") == "mag_training_event.v1"
    rows = te.read_events(limit=5, pattern="route_decision")
    assert any(r.get("event_id") == row.get("event_id") for r in rows)


def test_export_jsonl(tmp_path, monkeypatch):
    from mag import training_events as te

    monkeypatch.setattr(te, "EVENTS_PATH", tmp_path / "events.jsonl")
    te.emit(
        "fkb_failure",
        join={"task_id": "test-task"},
        outcome={"success": True},
        pattern_tags=["empty_reply"],
    )
    res = te.export_jsonl(dest=tmp_path / "out.jsonl")
    assert res.get("ok") is True
    assert res.get("n_exported", 0) >= 1
    assert (tmp_path / "out.jsonl").is_file()


def test_stats():
    from mag.training_events import stats

    s = stats()
    assert "by_pattern" in s
