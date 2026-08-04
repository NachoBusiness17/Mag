"""Operator inbox — deferred guidance + behavioral event logging."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mag import operator_inbox as inbox


@pytest.fixture(autouse=True)
def _isolate_inbox(tmp_path, monkeypatch):
    inbox_path = tmp_path / "operator_inbox.json"
    events_path = tmp_path / "behavioral_events.jsonl"
    monkeypatch.setattr(inbox, "INBOX_PATH", inbox_path)
    monkeypatch.setattr(inbox, "EVENTS_PATH", events_path)
    yield


def test_commit_and_status():
    r = inbox.commit_guidance("Focus on dashboard Body tab wiring only", source="test")
    assert r["ok"]
    st = inbox.status()
    assert st["pending_n"] == 1
    assert st["pending"][0]["text"].startswith("Focus on dashboard")


def test_drain_clear_vs_socratic():
    inbox.commit_guidance("Focus on dashboard Body tab wiring only")
    inbox.commit_guidance("continue")
    actions = inbox.drain_pending_at_checkpoint(task_hint="build inbox UI")
    kinds = {a["action"] for a in actions}
    assert "apply" in kinds
    assert "socratic" in kinds
    st = inbox.status()
    assert st["pending_n"] == 0


def test_apply_actions_injects_messages():
    actions = [{"action": "apply", "text": "Wire REST routes first", "task_hint": "inbox"}]
    msgs = inbox.apply_actions_to_messages([{"role": "user", "content": "hello"}], actions)
    assert len(msgs) == 2
    assert "OPERATOR GUIDANCE" in msgs[-1]["content"]
    assert "Wire REST routes" in msgs[-1]["content"]


def test_log_behavioral_event(tmp_path):
    inbox.log_behavioral_event(kind="collapse", detail="5x identical tool calls", tool="grep")
    rows = inbox.EVENTS_PATH.read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 1
    row = json.loads(rows[0])
    assert row["kind"] == "collapse"


def test_pending_hints_non_destructive():
    inbox.commit_guidance("dashboard operator inbox API")
    hints = inbox.pending_hints()
    assert len(hints) == 1
    assert inbox.status()["pending_n"] == 1
