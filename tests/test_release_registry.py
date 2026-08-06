"""Release registry + release_milestone training events."""
from __future__ import annotations

import json

import pytest

from mag import release_registry as rr
from mag import training_events as te


def test_status_summary_lists_versions():
    res = rr.status_summary()
    assert res.get("ok") is True
    ids = [r["id"] for r in res.get("releases") or []]
    assert "v1" in ids
    assert "v2" in ids
    assert "v5" in ids


def test_record_gate_writes_log_and_event(tmp_path, monkeypatch):
    gates = tmp_path / "memory" / "improve" / "releases" / "gates.jsonl"
    events = tmp_path / "memory" / "training" / "events.jsonl"
    gates.parent.mkdir(parents=True, exist_ok=True)
    events.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(rr, "GATES_LOG", gates)
    monkeypatch.setattr(te, "EVENTS_PATH", events)

    res = rr.record_gate("v2", "run_a", ok=True, note="smoke test")
    assert res.get("ok") is True

    lines = gates.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["version"] == "v2"
    assert row["gate_id"] == "run_a"
    assert row["ok"] is True

    evs = te.read_events(limit=5, pattern="release_milestone")
    assert evs
    assert evs[-1].get("pattern") == "release_milestone"


def test_unknown_version_record_fails():
    res = rr.record_gate("v99", "run_a", ok=True)
    assert res.get("ok") is False
