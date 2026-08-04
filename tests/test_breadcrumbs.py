"""Breadcrumbs — drop notes on the agent path without breaking stride."""
from __future__ import annotations

from pathlib import Path

import pytest

from mag import breadcrumbs, operator_inbox as inbox


@pytest.fixture(autouse=True)
def _isolate_inbox(tmp_path, monkeypatch):
    inbox_path = tmp_path / "operator_inbox.json"
    events_path = tmp_path / "behavioral_events.jsonl"
    monkeypatch.setattr(inbox, "INBOX_PATH", inbox_path)
    monkeypatch.setattr(inbox, "EVENTS_PATH", events_path)
    yield


def test_drop_breadcrumb_plain():
    r = breadcrumbs.drop_breadcrumb("Focus on dashboard Body tab only", refine=False)
    assert r["ok"]
    assert r["item"]["kind"] == "breadcrumb"
    st = breadcrumbs.status()
    assert st["pending_n"] == 1
    assert "breadcrumb" in st["layman"].lower()


def test_drop_breadcrumb_with_refine_flag():
    r = breadcrumbs.drop_breadcrumb("Riff on operator map simplification", refine=True)
    assert r["ok"]
    assert r["item"]["refine"] is True


def test_path_drop_expands_file(monkeypatch, tmp_path):
    monkeypatch.setattr(breadcrumbs, "ROOT", tmp_path)
    note = tmp_path / "crumb.md"
    note.write_text("check the Body tab wiring", encoding="utf-8")
    r = breadcrumbs.drop_breadcrumb("@crumb.md")
    assert r["ok"]
    assert "Body tab wiring" in r["item"]["text"]
    assert r["item"]["path"] == "crumb.md"


def test_drain_refine_spawns_queue(monkeypatch):
    queued: list[str] = []

    def fake_enqueue(goal, **kwargs):
        queued.append(goal)
        return {"queue_id": "q-test-1"}

    monkeypatch.setattr("mag.orchestrator.enqueue", fake_enqueue)
    breadcrumbs.drop_breadcrumb("Wire breadcrumb trail in dashboard app.js", refine=True)
    actions = inbox.drain_pending_at_checkpoint(task_hint="breadcrumb UI")
    kinds = {a.get("action") for a in actions}
    assert "apply" in kinds
    assert "refine_spawn" in kinds
    assert queued and "[refine breadcrumb]" in queued[0]


def test_breadcrumb_inject_label():
    actions = [
        {
            "action": "apply",
            "text": "Look at configs/lanes.yaml",
            "kind": "breadcrumb",
            "refine": False,
        }
    ]
    msgs = inbox.apply_actions_to_messages([{"role": "user", "content": "go"}], actions)
    assert "OPERATOR BREADCRUMB" in msgs[-1]["content"]
    assert "Incorporate into your current line of work" in msgs[-1]["content"]
